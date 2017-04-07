import datetime
import importlib
import inspect
import json
import os
import sys
from os.path import realpath
from os.path import dirname
from os.path import join
from os.path import basename

import asyncio

from config import config
from bot.model import User
from bot.model import TelegramUpdate
from bot.model import DownloadTask
from bot.model import StartSession
from ext.botan_async import track
from ext.evernote.client import Evernote
from ext.telegram.bot import TelegramBot
from ext.telegram.bot import TelegramBotError
from ext.telegram.models import Message
from ext.telegram.models import CallbackQuery


def get_commands(cmd_dir=None):
    commands = []
    commands_module = importlib.import_module('bot.commands')
    for cmd_name, class_name in config['commands'].items():
        klass = getattr(commands_module, class_name)
        commands.append(klass)
    return commands


class EvernoteBot(TelegramBot):

    def __init__(self, token, name):
        super(EvernoteBot, self).__init__(token, name)
        self.evernote = Evernote(title_prefix='[TELEGRAM BOT]')
        for cmd_class in get_commands():
            self.add_command(cmd_class)

    def track(self, message: Message):
        asyncio.ensure_future(track(message.user.id, message.raw))

    async def set_current_notebook(self, user, notebook_name=None,
                                   notebook_guid=None):
        query = {}
        if notebook_name is not None:
            query['name'] = notebook_name
        if notebook_guid is not None:
            query['guid'] = notebook_guid
        notebooks = await self.evernote.list_notebooks(
            user.evernote_access_token, query
        )
        if not notebooks:
            message = 'Notebook {name} (guid={guid}) not found (user {uid})'.format(
                name=notebook_name, guid=notebook_guid, uid=user.id
            )
            self.logger.warn(message)
            self.send_message(user.telegram_chat_id, 'Please, select notebook')
            return

        notebook = notebooks[0]
        user.current_notebook = notebook
        notebook_name = notebook_name or notebook['name']
        self.send_message(
            user.telegram_chat_id,
            'From now your current notebook is: {}'.format(notebook_name),
            {'hide_keyboard': True}
        )
        if user.mode == 'one_note':
            note_guid = await self.evernote.create_note(
                user.evernote_access_token,
                'Note for Evernoterobot',
                '',
                notebook['guid']
            )
            user.places[notebook['guid']] = note_guid
            user.save()
            note_link = await self.evernote.get_note_link(
                user.evernote_access_token, note_guid
            )
            message = 'You are in "One note" mode. From now all your \
notes will be saved in <a href="{0}">this note</a>'.format(note_link)
            self.send_message(user.telegram_chat_id, message,
                              parse_mode='Html')

    async def set_mode(self, user, mode): # TODO:
        text_mode = '{0}'.format(mode)
        mode = mode.replace(' ', '_').lower()
        chat_id = user.telegram_chat_id
        # TODO: check user.mode == mode
        if mode != 'one_note':
            user.mode = mode
            self.send_message(
                chat_id,
                'From now this bot in mode "{0}"'.format(text_mode),
                {'hide_keyboard': True}
            )
            return
        # 'one_note' mode required full permissions
        if user.settings.get('evernote_access', 'basic') != 'full':
            await self.request_full_permissions(user)
            return

        user.mode = mode
        reply = await self.send_message(chat_id, 'Please wait')
        note_guid = await self.evernote.create_note(
            user.evernote_access_token,
            'Note for Evernoterobot',
            '',
            user.current_notebook['guid']
        )
        user.places[user.current_notebook['guid']] = note_guid

        text = 'Bot switched to mode "{0}"'.format(text_mode)
        asyncio.ensure_future(
            self.api.editMessageText(chat_id, reply['message_id'], text)
        )
        text = 'New note was created in notebook "{0}"'.format(
            user.current_notebook['name']
        )
        self.send_message(chat_id, text, {'hide_keyboard': True})

    async def request_full_permissions(self, user):
        chat_id = user.telegram_chat_id
        text = 'To enable "One note" mode you should allow to bot to \
read and update your notes'
        res = self.send_message(chat_id, text, {'hide_keyboard': True})
        await asyncio.wait([res])
        text = 'Please tap on button below to give access to bot.'
        signin_button = {
            'text': 'Waiting for Evernote...',
            'url': self.url,
        }
        inline_keyboard = {'inline_keyboard': [[signin_button]]}
        message_future = self.send_message(chat_id, text, inline_keyboard)
        config_data = config['evernote']['full_access']
        session = StartSession.get({'id': user.id})
        oauth_data = await self.evernote.get_oauth_data(user.id, config_data,
                                                        session.key)
        session.oauth_data = oauth_data
        signin_button['text'] = 'Allow read and update notes to bot'
        signin_button['url'] = oauth_data['oauth_url']
        await asyncio.wait([message_future])
        msg = message_future.result()
        asyncio.ensure_future(
            self.api.editMessageReplyMarkup(
                chat_id,
                msg['message_id'],
                json.dumps(inline_keyboard)
            )
        )
        session.save()

    async def accept_request(self, user: User, request_type: str, message: Message):
        reply = await self.async_send_message(user.telegram_chat_id, '🔄 Accepted')
        TelegramUpdate.create(user_id=user.id,
                              request_type=request_type,
                              status_message_id=reply['message_id'],
                              message=message.raw)

    async def handle_callback_query(self, query: CallbackQuery):
        data = json.loads(query.data)
        if data['cmd'] == 'set_nb':
            user = User.get({'id': query.user.id})
            await self.set_current_notebook(user, notebook_guid=data['nb'])

    async def on_message_received(self, message: Message):
        self.track(message)
        user_id = message.user.id
        if '/start' in message.bot_commands:
            return

        if User.count({'id': user_id}) == 0:
            if StartSession.count({'id': user_id}) > 0:
                message_text = 'Please, sign in to Evernote account first: /start'
                error_text = 'User {0} not authorized in Evernote'.format(user_id)
            else:
                message_text = 'Who are you, stranger? Please, send /start command.'
                error_text = 'Unregistered user {0}'.format(user_id)
            self.send_message(message.chat.id, message_text)
            raise TelegramBotError(error_text)

        user = User.get({'id': user_id})
        if not hasattr(user, 'evernote_access_token') or \
           not user.evernote_access_token:
            self.send_message(
                user.telegram_chat_id,
                'You should authorize first. Please, send /start command.'
            )
            raise TelegramBotError(
                'User {0} not authorized in Evernote'.format(user.id)
            )
        user.last_request_time = datetime.datetime.now()
        user.save()

    async def on_text(self, message: Message):
        user = User.get({'id': message.user.id})
        text = message.text
        if user.state == 'select_notebook':
            if text.startswith('> ') and text.endswith(' <'):
                text = text[2:-2]
            await self.set_current_notebook(user, text)
            user.state = None
            user.save()
        elif user.state == 'switch_mode':
            if text.startswith('> ') and text.endswith(' <'):
                text = text[2:-2]
            await self.set_mode(user, text)
            user.state = None
            user.save()
        else:
            await self.accept_request(user, 'text', message)

    async def on_photo(self, message: Message):
        user = User.get({'id': message.user.id})
        await self.accept_request(user, 'photo', message)
        files = sorted(message.photos, key=lambda x: x.file_size,
                       reverse=True)
        DownloadTask.create(user_id=user.id,
                            file_id=files[0].file_id,
                            file_size=files[0].file_size,
                            completed=False)

    async def on_video(self, message: Message):
        user = User.get({'id': message.user.id})
        await self.accept_request(user, 'video', message)
        video = message.video
        DownloadTask.create(user_id=user.id,
                            file_id=video.file_id,
                            file_size=video.file_size,
                            completed=False)

    async def on_document(self, message: Message):
        user = User.get({'id': message.user.id})
        await self.accept_request(user, 'document', message)
        document = message.document
        DownloadTask.create(user_id=user.id,
                            file_id=document.file_id,
                            file_size=document.file_size,
                            completed=False)

    async def on_voice(self, message: Message):
        user = User.get({'id': message.user.id})
        voice = message.voice
        DownloadTask.create(user_id=user.id,
                            file_id=voice.file_id,
                            file_size=voice.file_size,
                            completed=False)
        await self.accept_request(user, 'voice', message)

    async def on_location(self, message: Message):
        user = User.get({'id': message.user.id})
        await self.accept_request(user, 'location', message)
