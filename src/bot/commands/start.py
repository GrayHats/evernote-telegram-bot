import json

import asyncio
import random
import string

from bot.model import StartSession
from ext.telegram.bot import TelegramBotCommand
from ext.telegram.models import Message


class StartCommand(TelegramBotCommand):

    name = 'start'

    async def execute(self, message: Message):
        chat_id = message.chat.id
        user_id = message.user.id
        self.bot.track(message)
        config = self.bot.config['evernote']['basic_access']
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
        oauth_data = await self.bot.evernote_api.get_oauth_data(
            user_id, config['key'], config['secret'],
            config['oauth_callback'], session_key
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
