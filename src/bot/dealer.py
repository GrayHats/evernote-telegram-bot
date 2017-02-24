import asyncio
import logging
import time
import traceback

import settings
from bot import EvernoteBot
from bot.message_handlers import TextHandler, PhotoHandler, VideoHandler, \
    DocumentHandler, VoiceHandler, LocationHandler
from bot.model import TelegramUpdate, User, FailedUpdate
from ext.evernote.api import TokenExpired
from ext.telegram.api import BotApi


class EvernoteDealer:

    def __init__(self, loop=None):
        self.logger = logging.getLogger('dealer')
        self._telegram_api = BotApi(settings.TELEGRAM['token'])
        self.__loop = loop or asyncio.get_event_loop()
        self.__handlers = {}

        self.register_handler('text', TextHandler)
        self.register_handler('photo', PhotoHandler)
        self.register_handler('video', VideoHandler)
        self.register_handler('document', DocumentHandler)
        self.register_handler('voice', VoiceHandler)
        self.register_handler('location', LocationHandler)

    def run(self):
        try:
            asyncio.ensure_future(self.async_run())
            self.__loop.run_forever()
            self.logger.info('Dealer done.')
        except Exception as e:
            self.logger.fatal('Dealer fail')
            self.logger.fatal(e, exc_info=1)

    async def async_run(self):
        try:
            while True:
                updates_by_user = self.fetch_updates()
                if not updates_by_user:
                    await asyncio.sleep(0.1)
                    continue
                for user_id, updates in updates_by_user.items():
                    try:
                        user = User.get({'id': user_id})
                        asyncio.ensure_future(
                            self.process_user_updates(user, updates)
                        )
                    except Exception as e:
                        message = "Can't process updates for user \
{0}\n{1}".format(user_id, e)
                        self.logger.error(message, exc_info=1)
        except Exception:
            self.logger.fatal('Dealer DOWN!!!', exc_info=1)

    def fetch_updates(self):
        self.logger.debug('Fetching telegram updates...')
        updates_by_user = {}
        try:
            fetched_updates = []
            for entry in TelegramUpdate.find({'in_process': {'$exists': False}}, [('created', 1)]):
                update = entry.update(
                    {'in_process': {'$exists': False}},
                    {'in_process': True}
                )
                fetched_updates.append(update)
            self.logger.debug('Fetched {0} updates'.format(len(fetched_updates)))

            for update in fetched_updates:
                user_id = update.user_id
                if not updates_by_user.get(user_id):
                    updates_by_user[user_id] = []
                updates_by_user[user_id].append(update)
        except Exception as e:
            err = "{0}\nCan't load telegram updates from mongo".format(e)
            self.logger.error(err, exc_info=1)
        return updates_by_user

    async def process_user_updates(self, user, update_list):
        start_ts = time.time()
        self.logger.debug('Start update list processing (user_id = {0})'.format(user.id))
        for update in update_list:
            try:
                for handler in self.__handlers[update.request_type]:
                    await handler.execute(user, update)

                text = '✅ {0} saved ({1:.2} s)'.format(update.request_type.capitalize(), time.time() - start_ts)
                asyncio.ensure_future(self._telegram_api.editMessageText(user.telegram_chat_id, update.status_message_id, text))
            except TokenExpired:
                asyncio.ensure_future(
                    self.edit_telegram_message(user.telegram_chat_id, update.status_message_id, '⛔️ Evernote access token is expired. Send /start to get new token')
                )
            except Exception as e:
                self.logger.error(e, exc_info=1)
                FailedUpdate.create(error=traceback.format_exc(), **update.save_data())
                asyncio.ensure_future(
                    self.edit_telegram_message(
                        user.telegram_chat_id,
                        update.status_message_id,
                        '❌ Something went wrong. Please, try again'
                    )
                )

        self.logger.debug('Cleaning up...')
        for update in update_list:
            for handler in self.__handlers[update.request_type]:
                await handler.cleanup(user, update)

        self.logger.debug('Done. (user_id = {0}). Processing takes {1} s'.format(user.id, time.time() - start_ts))

    async def edit_telegram_message(self, chat_id, message_id, text):
        bot = EvernoteBot(settings.TELEGRAM['token'], 'evernoterobot')
        asyncio.ensure_future(bot.api.editMessageText(chat_id, message_id, text))

    def register_handler(self, request_type, handler_class):
        if not self.__handlers.get(request_type):
            self.__handlers[request_type] = []
        self.__handlers[request_type].append(handler_class())
