#!/usr/bin/env python3

import sys
import argparse
from os.path import dirname
from os.path import realpath
from os.path import join

sys.path.append(dirname(realpath(dirname(__file__))))

from bot.downloader import TelegramDownloader
from daemons.daemon import Daemon
from config import config


class TelegramDownloaderDaemon(Daemon):

    def __init__(self, telegram_token, pidfile, download_dir=None):
        super().__init__(pidfile)
        self.download_dir = download_dir
        self.token = telegram_token

    def run(self):
        downloader = TelegramDownloader(self.token, self.download_dir)
        downloader.run()


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('CMD')
        args = parser.parse_args()
        cmd = args.CMD

        daemon = TelegramDownloaderDaemon(
            config['telegram']['token'],
            join(config['project_dir'], 'downloader.pid'),
            config['downloads_dir']
        )
        if cmd == 'start':
            daemon.start()
        elif cmd == 'stop':
            daemon.stop()
        elif cmd == 'restart':
            daemon.restart()
        else:
            print("Unknown command '{}'\n".format(cmd))
            sys.exit(1)
        print('OK')
    except Exception:
        print('FAILED')
        import traceback
        print(traceback.format_exc())
