import os
import random
import shutil
import string
from os.path import dirname
from os.path import join
from os.path import realpath
from os.path import exists

import pytest


@pytest.mark.skip(reason='TODO:')
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
    # TODO:
    shutil.rmtree(tmp_dir)
