import asyncio
import logging
import json
from abc import abstractmethod

from ext.telegram.api import BotApi
from ext.telegram.models import TelegramUpdate, Message, CallbackQuery


class TelegramBotError(Exception):
    def __init__(self, message, reply_markup=None):
        super(TelegramBotError, self).__init__(message)
        self.message = message
        self.reply_markup = reply_markup


class TelegramBot:

    def __init__(self, token, bot_name, **kwargs):
        self.api = BotApi(token)
        self.name = bot_name
        self.url = 'https://telegram.me/%s' % bot_name
        self.logger = logging.getLogger('bot')
        self.commands = {}
        if kwargs:
            map(lambda name, value: setattr(self, name, value), kwargs.items())

    def add_command(self, command_class, force=False):
        cmd_name = command_class.name
        if cmd_name in self.commands and not force:
            raise TelegramBotError('Command "%s" already exists' % cmd_name)
        self.commands[cmd_name] = command_class

    async def handle_update(self, data: dict):
        try:
            update = TelegramUpdate(data)
            await self.on_before_handle_update(update)

            if update.callback_query:
                await self.handle_callback_query(update.callback_query)
            elif update.message:
                await self.handle_message(update.message)
            # TODO: process inline query
            # TODO: process inline result
            # TODO: process callback query
        except Exception as e:
            message = 'Error: {0}\nData: {1}\n\n'.format(e, data)
            self.logger.error(message, exc_info=1)

    async def handle_callback_query(self, query: CallbackQuery):
        pass

    async def handle_message(self, message: Message):
        await self.on_message_received(message)
        text = message.text
        if text and text.startswith('/') and message.bot_commands:
            cmd = text.replace('/', '').strip()
            if cmd in self.commands:
                await self.execute_command(cmd, message)
        elif hasattr(message, 'photos') and message.photos:
            await self.on_photo(message)
        elif hasattr(message, 'video') and message.video:
            await self.on_video(message)
        elif hasattr(message, 'document') and message.document:
            await self.on_document(message)
        elif hasattr(message, 'voice') and message.voice:
            await self.on_voice(message)
        elif hasattr(message, 'location') and message.location:
            await self.on_location(message)
        elif text:
            await self.on_text(message)

        await self.on_message_processed(message)

    async def execute_command(self, cmd_name: str, message: Message):
        CommandClass = self.commands.get(cmd_name)
        if not CommandClass:
            raise TelegramBotError('Command "%s" not found' % cmd_name)
        obj = CommandClass(self)
        await obj.execute(message)

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        if reply_markup:
            reply_markup = json.dumps(reply_markup)
        return asyncio.ensure_future(
            self.api.sendMessage(chat_id, text, reply_markup, parse_mode)
        )

    async def async_send_message(self, chat_id, text, reply_markup=None,
                                 parse_mode=None):
        if reply_markup:
            reply_markup = json.dumps(reply_markup)
        return await self.api.sendMessage(chat_id, text, reply_markup, parse_mode)

    async def on_before_handle_update(self, update: TelegramUpdate):
        pass

    async def on_message_received(self, message: Message):
        pass

    async def on_message_processed(self, message: Message):
        pass

    async def on_photo(self, message: Message):
        pass

    async def on_video(self, message: Message):
        pass

    async def on_document(self, message: Message):
        pass

    async def on_voice(self, message: Message):
        pass

    async def on_location(self, message: Message):
        pass

    async def on_text(self, message: Message):
        pass


class TelegramBotCommand:

    name = 'command_name'

    def __init__(self, bot: TelegramBot):
        self.bot = bot
        assert self.__class__.name != 'command_name',\
            'You must define command name with "name" class attribute'

    @abstractmethod
    async def execute(self, message: Message):
        pass
