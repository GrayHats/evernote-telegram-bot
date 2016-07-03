import inspect
import importlib
import os
import sys
from os.path import realpath, dirname, join
import json

import aiomcache

from telegram.bot import TelegramBot, TelegramBotCommand
from bot.model import User, ModelNotFound, TelegramUpdate
from ext.evernote.client import EvernoteClient
import settings


def get_commands(cmd_dir=None):
    commands = []
    if cmd_dir is None:
        cmd_dir = join(realpath(dirname(__file__)), 'commands')
    exclude_modules = ['__init__']
    for dirpath, dirnames, filenames in os.walk(cmd_dir):
        for filename in filenames:
            file_path = join(dirpath, filename)
            ext = file_path.split('.')[-1]
            if ext in ['py']:
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
        self.evernote = EvernoteClient(
            settings.EVERNOTE['key'],
            settings.EVERNOTE['secret'],
            settings.EVERNOTE['oauth_callback'],
            sandbox=settings.DEBUG
        )
        self.cache = aiomcache.Client("127.0.0.1", 11211)
        for cmd_class in get_commands():
            self.add_command(cmd_class)

    async def list_notebooks(self, user):
        key = "list_notebooks_{0}".format(user.user_id).encode()
        data = await self.cache.get(key)
        if not data:
            access_token = user.evernote_access_token
            notebooks = [{'guid': nb.guid, 'name': nb.name} for nb in
                         self.evernote.list_notebooks(access_token)]
            await self.cache.set(key, json.dumps(notebooks).encode())
        else:
            notebooks = json.loads(data.decode())
        return notebooks

    async def update_notebooks_cache(self, user):
        key = "list_notebooks_{0}".format(user.user_id).encode()
        access_token = user.evernote_access_token
        notebooks = [{'guid': nb.guid, 'name': nb.name} for nb in
                     self.evernote.list_notebooks(access_token)]
        await self.cache.set(key, json.dumps(notebooks).encode())

    async def get_user(self, message):
        try:
            user = await User.get({'user_id': message['from']['id']})
            if user.telegram_chat_id != message['chat']['id']:
                user.telegram_chat_id = message['chat']['id']
                await user.save()
            return user
        except ModelNotFound:
            self.logger.warn("User %s not found" % message['from']['id'])

    async def set_current_notebook(self, user, notebook_name):
        all_notebooks = await self.list_notebooks(user)
        for notebook in all_notebooks:
            if notebook['name'] == notebook_name:
                reply = await self.api.sendMessage(
                    user.telegram_chat_id, 'Please wait',
                    reply_markup=json.dumps({'hide_keyboard': True}))

                user.current_notebook = notebook
                user.state = None
                await user.save()

                if user.mode == 'one_note':
                    note_guid = self.evernote.create_note(
                        user.evernote_access_token, text='',
                        title='Note for Evernoterobot')
                    user.places[user.current_notebook['guid']] = note_guid
                    await user.save()

                await self.api.editMessageText(
                    user.telegram_chat_id, reply["message_id"],
                    'From now your current notebook is: %s' % notebook_name)
                break
        else:
            await self.api.sendMessage(user.telegram_chat_id,
                                       'Please, select notebook')

    async def set_mode(self, user, mode):
        reply = await self.api.sendMessage(
            user.telegram_chat_id, 'Please wait',
            reply_markup=json.dumps({'hide_keyboard': True}))

        if mode.startswith('> ') and mode.endswith(' <'):
            mode = mode[2:-2]
        user.mode = mode.replace(' ', '_').lower()
        await user.save()
        text_mode = user.mode.capitalize().replace('_', ' ')
        if user.mode == 'one_note':
            note_guid = self.evernote.create_note(
                user.evernote_access_token, text='',
                title='Note for Evernoterobot')
            user.places[user.current_notebook['guid']] = note_guid
            await user.save()
            text = 'From now this bot in mode "{0}". It means that all messages you send will be saved in one (same) evernote note'.format(text_mode)
        if user.mode == 'multiple_notes':
            text = 'From now this bot in mode "{0}", It means that for every message you send will be created separate evernote note'.format(text_mode)

        await self.api.editMessageText(
            user.telegram_chat_id, reply["message_id"], text)

    async def accept_request(self, user, request_type, data):
        reply = await self.api.sendMessage(user.telegram_chat_id,
                                           '🔄 Accepted')
        await TelegramUpdate.create(user_id=user.user_id,
                                    request_type=request_type,
                                    status_message_id=reply['message_id'],
                                    data=data)

    async def on_text(self, user, message, text):
        if user.state == 'select_notebook':
            if text.startswith('> ') and text.endswith(' <'):
                text = text[2:-2]
            await self.set_current_notebook(user, text)
        if user.state == 'switch_mode':
            await self.set_mode(user, text)
        else:
            await self.accept_request(user, 'text', message)

    async def on_photo(self, user, message):
        await self.accept_request(user, 'photo', message)

    async def on_document(self, user, message):
        await self.accept_request(user, 'document', message)

    async def on_voice(self, user, message):
        await self.accept_request(user, 'voice', message)

    async def on_location(self, user, message):
        await self.accept_request(user, 'location', message)
