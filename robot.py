#!/usr/bin/env python3

import argparse
import logging.config
import sys
import os
import signal
import time
import asyncio
from os.path import join
import importlib
from aiohttp import web as aioweb

from src.utils.logs import get_config


def green(text):
    return "\033[92m%s\033[0m" % text


def red(text):
    return "\033[91m%s\033[0m" % text


def check_process(pidfile):
    if os.path.exists(pidfile):
        with open(pidfile) as f:
            pid = int(f.read())
            try:
                os.kill(pid, 0)
            except OSError:
                os.unlink(pidfile)
                return False
            else:
                return True
    return False


def get_pid(pidfile):
    with open(pidfile) as f:
        pid = int(f.read())
        return pid


def commands(cls):
    for name, method in cls.__dict__.items():
        if hasattr(method, 'cmd'):
            cls.commands.append(method.__name__)
    return cls


def cmd(method):
    method.cmd = True
    return method


@commands
class BotService:

    commands = []

    def __init__(self, config_file):
        os.environ['EVERNOTEROBOT_CONFIG'] = config_file
        config = importlib.import_module('src.config')
        self.config = config.config
        log_config = get_config(
            self.config['project_name'],
            self.config['logs_dir'],
            self.config['smtp']
        )
        logging.config.dictConfig(log_config)

    def __start_process(name, cmd, pidfile):
        print('Starting {}'.format(name), end="")
        os.system(cmd)
        time.sleep(1)
        if check_process(pidfile):
            print(green('OK'))
        else:
            print(red('FAILED'))

    @cmd
    def start(self, use_gunicorn=False):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)

        if not use_gunicorn:
            # import here because there are import config that reads file. Some little optimization
            from src.web.webapp import app
            aioweb.run_app(app)
            sys.exit(0)

        gunicorn_pidfile = join(self.config['project_dir'], 'gunicorn.pid')
        import gunicorn_config

        if os.path.exists(gunicorn_pidfile):
            print("Gunicorn already running")
            sys.exit(0)
        # Gunicorn
        self.__start_process(
            'Gunicorn',
            'gunicorn --config {0} {1}'.format(
                join(self.config['project_dir'], 'src/gunicorn_config.py'),
                gunicorn_config.app_name
            ),
            gunicorn_pidfile
        )
        # Downloader daemon
        downloader_pidfile = join(self.config['project_dir'], 'downloader.pid')
        self.__start_process(
            'File downloader daemon',
            './downoader.py --pidfile={0} --token={1} --downloads_dir={2} start'.format(
                downloader_pidfile,
                self.config['telegram']['token'],
                self.config['downloads_dir']
            ),
            downloader_pidfile
        )
        # Dealer daemon
        dealer_pidfile = join(self.config['project_dir'], 'dealer.pid')
        self.__start_process(
            'Evernote dealer daemon',
            './dealer.py --pidfile={} start'.format(dealer_pidfile),
            dealer_pidfile
        )

    @cmd
    def stop(self):
        pass

    @cmd
    def restart(self):
        self.stop()
        self.start()

    @cmd
    def reload(self):
        pass


# root_dir = realpath(dirname(__file__))
# base_dir = join(root_dir, 'evernoterobot')
# sys.path.insert(0, base_dir)

# import gunicorn_config
# from daemons import EvernoteDealerDaemon, TelegramDownloaderDaemon
# import settings
# from ext.telegram.api import BotApi


# dealer_pidfile = join(root_dir, 'dealer.pid')
# downloader_pidfile = join(root_dir, 'downloader.pid')
# gunicorn_pidfile = gunicorn_config.pidfile


# def stop():
#     print('Stopping dealer...')
#     EvernoteDealerDaemon(dealer_pidfile).stop()
#     print('Stopping downloader...')
#     TelegramDownloaderDaemon(downloader_pidfile).stop()

#     print('Stopping gunicorn...', end="")
#     try:
#         os.kill(get_pid(gunicorn_pidfile), signal.SIGTERM)
#         os.unlink(gunicorn_pidfile)
#         print(green('OK'))
#     except Exception:
#         if check_process(gunicorn_pidfile):
#             print(red('FAILED'))
#         else:
#             print(green('OK'))


# def status():
#     daemons = [
#         ('Gunicorn', gunicorn_pidfile),
#         ('Dealer', dealer_pidfile),
#         ('Downloader', downloader_pidfile)
#     ]
#     for service_name, pidfile in daemons:
#         print("{0} status: ".format(service_name), end="")
#         if check_process(pidfile):
#             print(green('Started'))
#         else:
#             print(red('Stopped'))


# def reload():
#     logging.config.dictConfig(settings.LOG_SETTINGS)
#     print("Reloading gunicorn... ", end="")
#     os.kill(get_pid(gunicorn_pidfile), signal.SIGHUP)
#     print(green('OK'))


# def set_webhook():
#     telegram_api = BotApi(settings.TELEGRAM['token'])
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(
#         telegram_api.setWebhook(settings.TELEGRAM['webhook_url'])
#     )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--gunicorn', action='store_true')
    hint_commands = '|'.join([cmd for cmd in BotService.commands])
    parser.add_argument(
        'CMD',
        help="Available commands:\n{0}".format(hint_commands)
    )
    args = parser.parse_args()
    cmd = args.CMD
    config_file = args.config
    use_gunicorn = args.gunicorn

    service = BotService(config_file)
    if cmd == 'start':
        service.start(use_gunicorn)
    elif cmd == 'stop':
        service.stop()
    elif cmd == 'restart':
        service.restart()
    elif cmd == 'reload':
        service.reload()
    elif cmd == 'status':
        service.status()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)

    print("Done.\n")
