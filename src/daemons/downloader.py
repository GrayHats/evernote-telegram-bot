import sys
import argparse
from bot.downloader import TelegramDownloader
from daemons.daemon import Daemon


class TelegramDownloaderDaemon(Daemon):

    def __init__(self, telegram_token, pidfile, download_dir=None):
        super().__init__(pidfile)
        self.download_dir = download_dir
        self.token = telegram_token

    def run(self):
        downloader = TelegramDownloader(self.token, self.download_dir)
        downloader.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pidfile', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--download_dir', required=True)
    parser.add_argument('CMD')
    args = parser.parse_args()
    cmd = args.CMD

    daemon = TelegramDownloaderDaemon(args.pidfile, args.download_dir)
    if cmd == 'start':
        daemon.start()
    elif cmd == 'stop':
        daemon.stop()
    elif cmd == 'restart':
        daemon.restart()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)
