import json
import asyncio
import random
import string

from config import config
from bot.model import User
from bot.model import StartSession
from ext.telegram.bot import TelegramBotCommand
from ext.telegram.models import Message


class StartCommand(TelegramBotCommand):

    name = 'start'

    async def execute(self, message: Message):
        chat_id = message.chat.id
        user_id = message.user.id
        session_key = ''.join(
            [random.choice(string.ascii_letters + string.digits)
             for i in range(32)]
        )
        welcome_text = '''Welcome! It's bot for saving your notes to Evernote on fly.
Please tap on button below to link your Evernote account with bot.'''
        signin_button = {
            'text': 'Waiting for Evernote...',
            'url': self.bot.url,
        }
        inline_keyboard = {'inline_keyboard': [[signin_button]]}
        welcome_message_future = self.bot.send_message(chat_id, welcome_text,
                                                       inline_keyboard)
        oauth_data = await self.bot.evernote.get_oauth_data(
            user_id, config['evernote']['basic_access'], session_key
        )
        session_data = {
            'user': {
                'username': message.user.username,
                'first_name': message.user.first_name,
                'last_name': message.user.last_name,
            },
            'chat_id': chat_id,
        }
        StartSession.create(id=user_id, key=session_key, data=session_data,
                            oauth_data=oauth_data)
        signin_button['text'] = 'Sign in to Evernote'
        signin_button['url'] = oauth_data['oauth_url']
        await asyncio.wait([welcome_message_future])
        msg = welcome_message_future.result()
        asyncio.ensure_future(
            self.bot.api.editMessageReplyMarkup(chat_id, msg['message_id'],
                                                json.dumps(inline_keyboard))
        )


class HelpCommand(TelegramBotCommand):

    name = 'help'

    async def execute(self, message: Message):
        text = '''This is bot for Evernote (https://evernote.com).

Just send message to bot and it creates note in your Evernote notebook. \
You can send to bot:

* text
* photo (size < 12 Mb) - Telegram restriction
* file (size < 12 Mb) - Telegram restriction
* voice message (size < 12 Mb) - Telegram restriction
* location

Bot can works in two modes
1) "One note" mode.
In this mode there are in evernote notebook will be created just one note. \
All messages you sent will be saved in this note.

2) "Multiple notes" mode.
In this mode for every message you sent there are in evernote notebook \
separate note will be created .

You can switch bot mode with command /switch_mode
Note that every time you select "One note" mode, new note will be created \
and set as current note for this bot.

Also, you can switch your current notebook with command /notebook
Note that every time you switch notebook in mode "One note", new note will \
be created in selected notebook.

We are sorry for low speed, but Evernote API are slow \
(about 1 sec per request).

Contacts: djudman@gmail.com
'''
        self.bot.send_message(message.chat.id, text)


class SwitchNotebookCommand(TelegramBotCommand):

    name = 'notebook'

    async def execute(self, message: Message):
        user = User.get({'id': message.user.id})
        notebooks = await self.bot.evernote.list_notebooks(
            user.evernote_access_token
        )
        buttons = []
        for notebook in notebooks:
            if notebook['guid'] == user.current_notebook['guid']:
                name = '> {} <'.format(notebook['name'])
            else:
                name = notebook['name']
            buttons.append({'text': name})
        self.bot.send_message(
            user.telegram_chat_id,
            'Please, select notebook',
            {
                'keyboard': [[b] for b in buttons],
                'resize_keyboard': True,
                'one_time_keyboard': True,
            }
        )
        user.state = 'select_notebook'
        user.save()


class SwitchModeCommand(TelegramBotCommand):

    name = 'switch_mode'

    async def execute(self, message: Message):
        user = User.get({'id': message.user.id})
        buttons = []
        for mode in ['one_note', 'multiple_notes']:
            if user.mode == mode:
                name = "> %s <" % mode.capitalize().replace('_', ' ')
            else:
                name = mode.capitalize().replace('_', ' ')
            buttons.append({'text': name})
        self.bot.send_message(
            user.telegram_chat_id,
            'Please, select mode',
            {
                'keyboard': [[b] for b in buttons],
                'resize_keyboard': True,
                'one_time_keyboard': True,
            }
        )
        user.state = 'switch_mode'
        user.save()
