import asyncio
import logging
import time
import traceback

from config import config
from bot.message_handlers import TextHandler
from bot.message_handlers import PhotoHandler
from bot.message_handlers import VideoHandler
from bot.message_handlers import DocumentHandler
from bot.message_handlers import VoiceHandler
from bot.message_handlers import LocationHandler
from bot.model import TelegramUpdate
from bot.model import User
from bot.model import FailedUpdate
from ext.evernote.api import TokenExpired
from ext.telegram.api import BotApi


class EvernoteDealer:
    '''
    This class can fetch telegram update(s) from storage and pass them to
    appropriate handler(s)
    '''

    def __init__(self, loop=None):
        self.__loop = loop or asyncio.get_event_loop()
        self.logger = logging.getLogger('dealer')
        self._telegram_api = BotApi(config['telegram']['token'])
        self.__handlers = {
            'text': [TextHandler],
            'photo': [PhotoHandler],
            'video': [VideoHandler],
            'document': [DocumentHandler],
            'voice': [VoiceHandler],
            'location': [LocationHandler],
        }

    def run(self):
        task = asyncio.ensure_future(self.async_run())
        self.__loop.run_until_complete(task)
        self.logger.fatal('Dealer down!')

    async def async_run(self):
        while True:
            updates_by_user = self.fetch_updates()
            if not updates_by_user:
                await asyncio.sleep(0.1)
                continue
            for user_id, updates in updates_by_user.items():
                user = User.get({'id': user_id})
                asyncio.ensure_future(self.process_user_updates(user, updates))

    def fetch_updates(self):
        self.logger.debug('Fetching telegram updates...')
        updates_by_user = {}
        try:
            fetched_updates = []
            # TODO: find and modify in one operation
            updates = TelegramUpdate.find({'in_process': {'$exists': False}},
                                          [('created', 1)])
            for entry in updates:
                update = entry.update(
                    {'in_process': {'$exists': False}},
                    {'in_process': True}
                )
                fetched_updates.append(update)
            self.logger.debug('Fetched {0} updates'.format(
                len(fetched_updates)
            ))

            for update in fetched_updates:
                user_id = update.user_id
                if not updates_by_user.get(user_id):
                    updates_by_user[user_id] = []
                updates_by_user[user_id].append(update)
        except Exception as e:
            err = "{0}\nCan't load telegram updates from mongo".format(e)
            self.logger.error(err, exc_info=1)
        return updates_by_user

    def update_status_message(self, user, update, text):
        return asyncio.ensure_future(
            self._telegram_api.editMessageText(
                user.telegram_chat_id, update.status_message_id, text
            )
        )

    async def process_user_updates(self, user, update_list):
        start_ts = time.time()
        self.logger.debug(
            'Start update list processing (user_id = {0})'.format(user.id)
        )
        for update in update_list:
            try:
                for handler in self.__handlers[update.request_type]:
                    await handler.execute(user, update)

                text = '✅ {0} saved ({1:.2} s)'.format(
                    update.request_type.capitalize(),
                    time.time() - start_ts
                )
                self.update_status_message(user, update, text)
            except TokenExpired:
                text = '⛔️ Evernote access token is expired. \
Send /start to get new token'
                self.update_status_message(user, update, text)
            except Exception as e:
                self.logger.error(e, exc_info=1)
                FailedUpdate.create(error=traceback.format_exc(),
                                    **update.save_data())
                text = '❌ Something went wrong. Please, try again'
                self.update_status_message(user, update, text)

        self.logger.debug('Cleaning up...')
        for update in update_list:
            for handler in self.__handlers[update.request_type]:
                await handler.cleanup(user, update)

        log_message = 'Done. (user_id = {0}). Processing takes {1} s'.format(
            user.id, time.time() - start_ts
        )
        self.logger.debug(log_message)
