import datetime
import importlib
import inspect
import json
import os
import sys
from os.path import realpath, dirname, join, basename

import aiomcache
import asyncio

import settings
from bot.model import User, ModelNotFound, TelegramUpdate, DownloadTask, \
    StartSession
from ext.botan_async import track
from ext.evernote.api import AsyncEvernoteApi
from ext.evernote.client import EvernoteClient
from ext.evernote.provider import NoteProvider
from ext.telegram.bot import TelegramBot, TelegramBotCommand, TelegramBotError
from ext.telegram.models import Message, CallbackQuery


def get_commands(cmd_dir=None):
    commands = []
    if cmd_dir is None:
        cmd_dir = join(realpath(dirname(__file__)), 'commands')
    exclude_modules = ['__init__']
    for dirpath, dirnames, filenames in os.walk(cmd_dir):
        if basename(dirpath) == 'tests':
            continue
        for filename in filenames:
            file_path = join(dirpath, filename)
            ext = file_path.split('.')[-1]
            if ext not in ['py']:
                continue
            sys_path = list(sys.path)
            sys.path.insert(0, cmd_dir)
            module_name = inspect.getmodulename(file_path)
            if module_name not in exclude_modules:
                module = importlib.import_module(module_name)
                sys.path = sys_path
                for name, klass in inspect.getmembers(module):
                    if inspect.isclass(klass) and\
                       issubclass(klass, TelegramBotCommand) and\
                       klass != TelegramBotCommand:
                            commands.append(klass)
    return commands


class EvernoteBot(TelegramBot):

    def __init__(self, token, name):
        super(EvernoteBot, self).__init__(token, name)
        config = settings.EVERNOTE['basic_access']
        self.evernote = EvernoteClient(config['key'], config['secret'], config['oauth_callback'], sandbox=settings.DEBUG)
        self.evernote_api = AsyncEvernoteApi()
        self.cache = aiomcache.Client("127.0.0.1", 11211)
        for cmd_class in get_commands():
            self.add_command(cmd_class)

    def track(self, message: Message):
        asyncio.ensure_future(track(message.user.id, message.raw))

    async def list_notebooks(self, user: User):
        key = "list_notebooks_{0}".format(user.id).encode()
        data = await self.cache.get(key)
        if not data:
            access_token = user.evernote_access_token
            list_notebooks = await self.evernote_api.list_notebooks(access_token)
            notebooks = [{'guid': nb.guid, 'name': nb.name} for nb in list_notebooks]
            await self.cache.set(key, json.dumps(notebooks).encode())
        else:
            notebooks = json.loads(data.decode())
        return notebooks

    async def update_notebooks_cache(self, user):
        key = "list_notebooks_{0}".format(user.id).encode()
        access_token = user.evernote_access_token
        list_notebooks = await self.evernote_api.list_notebooks(access_token)
        notebooks = [{'guid': nb.guid, 'name': nb.name} for nb in list_notebooks]
        await self.cache.set(key, json.dumps(notebooks).encode())

    async def set_current_notebook(self, user, notebook_name=None, notebook_guid=None):
        all_notebooks = await self.list_notebooks(user)
        for notebook in all_notebooks:
            if (notebook_guid and notebook_guid == notebook['guid']) or (notebook['name'] == notebook_name):
                user.current_notebook = notebook
                user.state = None
                user.save()
                notebook_name = notebook_name or notebook['name']
                asyncio.ensure_future(
                    self.api.sendMessage(
                        user.telegram_chat_id,
                        'From now your current notebook is: %s' % notebook_name,
                        reply_markup=json.dumps({'hide_keyboard': True})
                    )
                )
                if user.mode == 'one_note':
                    note_guid = await self.evernote_api.new_note(
                        user.evernote_access_token,
                        notebook_guid=notebook['guid'],
                        text='',
                        title='Note for Evernoterobot')
                    user.places[user.current_notebook['guid']] = note_guid
                    user.save()
                    note_link = await self.evernote_api.get_note_link(user.evernote_access_token, note_guid)
                    asyncio.ensure_future(
                        self.api.sendMessage(
                            user.telegram_chat_id,
                            'You are in "One note" mode. From now all your notes will be saved in <a href="{0}">this note</a>'.format(note_link),
                            parse_mode='Html'
                        )
                    )
                    await NoteProvider().get_note(user.evernote_access_token, note_guid)
                break
        else:
            asyncio.ensure_future(self.api.sendMessage(user.telegram_chat_id, 'Please, select notebook'))

    async def set_mode(self, user, mode):
        if mode.startswith('> ') and mode.endswith(' <'):
            mode = mode[2:-2]
        text_mode = '{0}'.format(mode)
        mode = mode.replace(' ', '_').lower()

        if mode == 'one_note':
            if user.settings.get('evernote_access', 'basic') == 'full':
                user.mode = mode
                reply = await self.api.sendMessage(user.telegram_chat_id, 'Please wait')
                notebook_guid = user.current_notebook['guid']
                # note_guid = await self.evernote_api.new_note(user.evernote_access_token, notebook_guid, text='', title='Note for Evernoterobot')
                note_guid = self.evernote.create_note(user.evernote_access_token, text='', title='Note for Evernoterobot')
                user.places[user.current_notebook['guid']] = note_guid

                text = 'Bot switched to mode "{0}"'.format(text_mode)
                asyncio.ensure_future(self.api.editMessageText(user.telegram_chat_id, reply["message_id"], text))
                text = 'New note was created in notebook "{0}"'.format(user.current_notebook['name'])
                asyncio.ensure_future(self.api.sendMessage(user.telegram_chat_id, text, json.dumps({'hide_keyboard': True})))
            else:
                text = 'To enable "One note" mode you should allow to bot to read and update your notes'
                await self.api.sendMessage(user.telegram_chat_id, text, json.dumps({'hide_keyboard': True}))
                text = 'Please tap on button below to give access to bot.'
                signin_button = {
                    'text': 'Waiting for Evernote...',
                    'url': self.url,
                }
                inline_keyboard = {'inline_keyboard': [[signin_button]]}
                message_future = asyncio.ensure_future(
                    self.api.sendMessage(user.telegram_chat_id,
                                         text,
                                         json.dumps(inline_keyboard))
                )
                config = settings.EVERNOTE['full_access']
                session = StartSession.get({'id': user.id})
                oauth_data = await self.evernote_api.get_oauth_data(user.id, config['key'], config['secret'], config['oauth_callback'], session.key)
                session.oauth_data = oauth_data
                signin_button['text'] = 'Allow read and update notes to bot'
                signin_button['url'] = oauth_data["oauth_url"]
                await asyncio.wait([message_future])
                msg = message_future.result()
                asyncio.ensure_future(self.api.editMessageReplyMarkup(user.telegram_chat_id, msg['message_id'], json.dumps(inline_keyboard)))
                session.save()
        else:
            user.mode = mode
            asyncio.ensure_future(
                self.api.sendMessage(user.telegram_chat_id,
                                     'From now this bot in mode "{0}"'.format(text_mode),
                                     reply_markup=json.dumps({'hide_keyboard': True}))
            )

        user.state = None
        user.save()

    def accept_request(self, user: User, request_type: str, message: Message):
        def on_message_sent(future_message):
            reply = future_message.result()
            TelegramUpdate.create(user_id=user.id,
                                  request_type=request_type,
                                  status_message_id=reply['message_id'],
                                  message=message.raw)

        future = asyncio.ensure_future(self.api.sendMessage(user.telegram_chat_id, '🔄 Accepted'))
        future.add_done_callback(on_message_sent)

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
        if User.count({'id': user_id}) > 0:
            user = User.get({'id': user_id})
            if not hasattr(user, 'evernote_access_token') or not user.evernote_access_token:
                await self.api.sendMessage(user.telegram_chat_id, 'You should authorize first. Please, send /start command.')
                raise TelegramBotError('User {0} not authorized in Evernote'.format(user.id))
            user.last_request_time = datetime.datetime.now()
            user.save()
        else:
            if StartSession.count({'id': user_id}) > 0:
                message_text = 'Please, sign in to Evernote account first: /start'
                error_text = 'User {0} not authorized in Evernote'.format(user_id)
            else:
                message_text = 'Who are you, stranger? Please, send /start command.'
                error_text = 'Unregistered user {0}'.format(user_id)
            asyncio.ensure_future(self.api.sendMessage(message.chat.id, message_text))
            raise TelegramBotError(error_text)


    async def on_text(self, message: Message):
        user = User.get({'id': message.user.id})
        text = message.text
        if user.state == 'select_notebook':
            if text.startswith('> ') and text.endswith(' <'):
                text = text[2:-2]
            await self.set_current_notebook(user, text)
        elif user.state == 'switch_mode':
            await self.set_mode(user, text)
        else:
            self.accept_request(user, 'text', message)

    async def on_photo(self, message: Message):
        user = User.get({'id': message.user.id})
        self.accept_request(user, 'photo', message)
        files = sorted(message.photos, key=lambda x: x.file_size,
                       reverse=True)
        DownloadTask.create(user_id=user.id,
                            file_id=files[0].file_id,
                            file_size=files[0].file_size,
                            completed=False)

    async def on_video(self, message: Message):
        user = User.get({'id': message.user.id})
        self.accept_request(user, 'video', message)
        video = message.video
        DownloadTask.create(user_id=user.id,
                            file_id=video.file_id,
                            file_size=video.file_size,
                            completed=False)

    async def on_document(self, message: Message):
        user = User.get({'id': message.user.id})
        self.accept_request(user, 'document', message)
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
        self.accept_request(user, 'voice', message)

    async def on_location(self, message: Message):
        user = User.get({'id': message.user.id})
        self.accept_request(user, 'location', message)
