import asyncio
import os

from utils.logs import get_logger
from utils.downloader import HttpDownloader
from utils.downloader import DownloadError
from bot import DownloadTask
from ext.telegram.api import BotApi


class TelegramDownloader(HttpDownloader):
    '''
    This class can take task from queue (in mongodb) and asynchronously \
    download file from Telegram servers to local directory.
    '''

    def __init__(self, bot_token, download_dir=None, *, loop=None):
        logger = get_logger('downloader')
        super().__init__(download_dir, logger=logger, loop=loop)
        self._telegram_api = BotApi(bot_token)
        self.tasks = []

    def run(self):
        self._loop.run_until_complete(self.async_run())
        self.logger.fatal('Downloader stopped')

    async def async_run(self):
        while True:
            try:
                tasks = self.download_all()
                if not tasks:
                    await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(e, exc_info=1)

    async def get_download_url(self, file_id):
        return await self._telegram_api.getFile(file_id)

    async def handle_download_task(self, task):
        try:
            file_id = task.file_id
            download_url = await self.get_download_url(file_id)
            destination_file = os.path.join(self.download_dir, file_id)
            response = await self.async_download_file(download_url,
                                                      destination_file)
            task.mime_type = response.headers.get(
                'CONTENT-TYPE',
                'application/octet-stream'
            )
            task.completed = True
            task.file = destination_file
            task.save()
        except DownloadError as e:
            self.logger.error(e, exc_info=1)
        except Exception as e:
            self.logger.error(e, exc_info=1)

    def download_all(self):
        futures = []
        # TODO: find and modify with one operation
        tasks = DownloadTask.find({'in_progress': {'$exists': False},
                                  'completed': False})
        for task in tasks:
            entry = task.update({'in_progress': {'$exists': False}},
                                {'in_progress': True})
            futures.append(
                asyncio.ensure_future(self.handle_download_task(entry))
            )
        return futures
