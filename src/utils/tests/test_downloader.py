from utils.downloader import HttpDownloader
import string
import random
import asyncio
import os


def test_download_file(*args):
    downloader = HttpDownloader()
    dest_filename = ''.join(
        [random.choice(string.ascii_lowercase) for x in range(10)]
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        downloader.async_download_file(
            'https://yandex.ru/robots.txt',
            dest_filename
        )
    )
    assert os.path.exists(dest_filename)
    with open(dest_filename) as f:
        assert (f.readline() == "# yandex.ru\n")
        assert (f.readline() == "User-agent: *\n")
    os.unlink(dest_filename)
