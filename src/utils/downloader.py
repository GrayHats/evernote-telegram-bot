import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

import aiohttp


class DownloadError(Exception):
    def __init__(self, http_status, response_text, download_url):
        super(DownloadError, self).__init__()
        self.status = http_status
        self.response = response_text
        self.download_url = download_url

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{0} - Response: {1}, {2}'.format(
            self.download_url, self.status, self.response)

    def __repr__(self):
        return 'DownloadError({0}, "{1}", "{2}")'.format(
            self.status, self.response, self.download_url)


class HttpDownloader:

    def __init__(self, download_dir=None, *, loop=None):
        self.logger = logging.getLogger('http_downloader')
        self._loop = loop or asyncio.get_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=10)
        if download_dir is None:
            download_dir = '/tmp'
            message = 'download_dir does not set. Used: "{0}"'.format(download_dir)
            self.logger.warn(message)
        if not os.path.exists(download_dir):
            message = 'Download directory {0} not found'.format(download_dir)
            raise FileNotFoundError(message)
        self.download_dir = download_dir

    def __write_file(self, destination_file, data):
        try:
            with open(destination_file, 'wb') as f:
                f.write(data)
            self.logger.debug('File {0} saved'.format(destination_file))
        except Exception as e:
            self.logger.error(e, exc_info=1)

    async def async_download_file(self, url, dest_file):
        self.logger.debug('Start downloading {0}'.format(url))
        with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    await self._loop.run_in_executor(
                        self._executor,
                        self.__write_file,
                        dest_file,
                        data
                    )
                    self.logger.debug('File saved to {0} ({1})'.format(dest_file, url))
                    return response
                else:
                    response_text = await response.text()
                    raise DownloadError(response.status, response_text, url)
