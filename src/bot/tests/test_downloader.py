import asyncio
import os
import random
import shutil
import string
from os.path import dirname
from os.path import join
from os.path import realpath
from os.path import exists

import pytest

from config import config
from bot.downloader import TelegramDownloader
from bot.model import DownloadTask


@pytest.mark.async_test
async def test_download_file():
    async def get_url(file_id):
        urls = {
            'robots': 'http://yandex.ru/robots.txt',
            'rpm': 'http://mirror.yandex.ru/altlinux/4.0/Desktop/4.0.0/files/i586/GConf-2.16.1-alt1.i586.rpm',
        }
        return urls[file_id]

    tmp_dir = join(realpath(dirname(__file__)), 'tmp')
    download_dir = join(tmp_dir, ''.join([random.choice(string.ascii_letters) for i in range(10)]))
    if not exists(download_dir):
        os.makedirs(download_dir)
    task = DownloadTask.create(file_id='rpm', completed=False)
    task2 = DownloadTask.create(file_id='robots', completed=False)
    downloader = TelegramDownloader(config['telegram']['token'], download_dir)
    downloader.get_download_url = get_url
    futures = downloader.download_all()
    await asyncio.wait(futures)
    task.delete()
    task2.delete()

    shutil.rmtree(tmp_dir)
