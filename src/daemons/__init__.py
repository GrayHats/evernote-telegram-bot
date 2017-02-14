from bot.dealer import EvernoteDealer
from bot.downloader import TelegramDownloader
from daemons.daemon import Daemon
from settings import TELEGRAM


class EvernoteDealerDaemon(Daemon):

    def run(self):
        dealer = EvernoteDealer()
        dealer.run()


class TelegramDownloaderDaemon(Daemon):

    def __init__(self, pidfile, download_dir=None):
        super().__init__(pidfile)
        self.download_dir = download_dir

    def run(self):
        downloader = TelegramDownloader(TELEGRAM['token'], self.download_dir)
        downloader.run()
