import asyncio
import time

from utils.logs import get_logger
from bot.message_handlers import TextHandler
from bot.message_handlers import PhotoHandler
from bot.message_handlers import VideoHandler
from bot.message_handlers import DocumentHandler
from bot.message_handlers import VoiceHandler
from bot.message_handlers import LocationHandler
from bot.model import TelegramUpdate
from bot.model import User
from utils.daemon import Daemon


class EvernoteDealer:
    '''
    This class can fetch telegram update(s) from storage and pass them to
    appropriate handler(s)
    '''

    def __init__(self, loop=None):
        self.__loop = loop or asyncio.get_event_loop()
        self.logger = get_logger('dealer')
        self.handlers = {
            'text': [TextHandler()],
            'photo': [PhotoHandler()],
            'video': [VideoHandler()],
            'document': [DocumentHandler()],
            'voice': [VoiceHandler()],
            'location': [LocationHandler()],
        }

    def run(self):
        task = asyncio.ensure_future(self.async_run())
        self.__loop.run_until_complete(task)
        self.logger.fatal('Dealer down!')

    async def async_run(self):
        while True:
            try:
                updates_by_user = self.fetch_updates()
            except Exception as e:
                err = "{0}\nCan't load telegram updates from mongo".format(e)
                self.logger.error(err, exc_info=1)
                updates_by_user = None
            if not updates_by_user:
                await asyncio.sleep(0.1)
                continue
            for user_id, updates in updates_by_user.items():
                user = User.get({'id': user_id})
                asyncio.ensure_future(self.process_user_updates(user, updates))

    def fetch_updates(self):
        self.logger.debug('Fetching telegram updates...')
        updates_by_user = {}
        fetched_updates = []
        # TODO: find and modify in one operation
        # updates = TelegramUpdate.find({'in_process': {'$exists': False}},
        #                               [('created', 1)])
        query = {'in_process': {'$exists': True}}
        update_query = {'$set': {'in_process': True}}
        sort = [('created', 1)]
        while True:
            update = TelegramUpdate.find_and_modify(query, update_query, sort)
            if not update:
                break
            fetched_updates.append(update)
        self.logger.debug('Fetched {} updates'.format(len(fetched_updates)))
        for update in fetched_updates:
            user_id = update.user_id
            if not updates_by_user.get(user_id):
                updates_by_user[user_id] = []
            updates_by_user[user_id].append(update)
        return updates_by_user

    async def process_user_updates(self, user, update_list):
        start_ts = time.time()
        self.logger.debug(
            'Start update list processing (user_id = {0})'.format(user.id)
        )
        for update in update_list:
            for handler in self.handlers[update.request_type]:
                await handler.execute(user, update)
        self.logger.debug('Cleaning up...')
        for update in update_list:
            for handler in self.handlers[update.request_type]:
                await handler.cleanup(user, update)

        log_message = 'Done. (user_id = {0}). Processing takes {1} s'.format(
            user.id, time.time() - start_ts
        )
        self.logger.debug(log_message)


class EvernoteDealerDaemon(Daemon):

    def run(self):
        dealer = EvernoteDealer()
        dealer.run()
