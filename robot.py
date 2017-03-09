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


def process_exists(pidfile):
    if not os.path.exists(pidfile):
        return False
    with open(pidfile) as f:
        pid = int(f.read())
        try:
            os.kill(pid, 0)
        except OSError:
            os.unlink(pidfile)
            return False
    return True


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
        self.services = {
            'gunicorn': {
                'pidfile': join(self.config['project_dir'], 'gunicorn.pid'),
                'exec_file': 'gunicorn',
            },
            'dealer': {
                'pidfile': join(self.config['project_dir'], 'dealer.pid'),
                'exec_file': join(self.config['project_dir'], 'src/daemons/dealer.py'),
            },
            'downloader': {
                'pidfile': join(self.config['project_dir'], 'downloader.pid'),
                'exec_file': join(self.config['project_dir'], 'src/daemons/downloader.py'),
            },
        }

    def __get_pidfile(self, service_name):
        pidfiles = {
            'dealer': join(self.config['project_dir'], 'dealer.pid'),
            'downloader': join(self.config['project_dir'], 'downloader.pid'),
            'gunicorn': join(self.config['project_dir'], 'gunicorn.pid')
        }
        return pidfiles[service_name]

    def __start_service(name, cmd, pidfile):
        print('Starting {}'.format(name), end="")
        os.system(cmd)
        time.sleep(1)
        if process_exists(pidfile):
            print(green('OK'))
        else:
            print(red('FAILED'))

    def __stop_service(self, service_name):
        print('Stopping {}...'.format(service_name), end="")
        pidfile = self.__get_pidfile(service_name)
        cmd = '{file} --pidfile={pidfile} stop'.format(
            file=join(self.config['project_dir'], 'src/daemons/{}.py'.format(service_name)),
            pidfile=pidfile
        )
        os.system(cmd)
        if not process_exists(pidfile):
            print(green('OK'))
        else:
            print(red('FAILED'))

    def __stop_process(process_name, pidfile):
        print('Stopping {}...'.format(process_name), end="")
        try:
            os.kill(get_pid(pidfile), signal.SIGTERM)
            os.unlink(pidfile)
            print(green('OK'))
        except Exception:
            if process_exists(pidfile):
                print(red('FAILED'))
            else:
                print(green('OK'))

    @cmd
    def start(self, use_gunicorn=False):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)

        if not use_gunicorn:
            # import here because there are import config that reads file.
            # Some little optimization
            from src.web.webapp import app
            aioweb.run_app(app)
            sys.exit(0)

        gunicorn_pidfile = join(self.config['project_dir'], 'gunicorn.pid')
        import gunicorn_config

        if os.path.exists(gunicorn_pidfile):
            print("Gunicorn already running")
            sys.exit(0)
        # Gunicorn
        self.__start_service(
            'Gunicorn',
            'gunicorn --config {0} {1}'.format(
                join(self.config['project_dir'], 'src/gunicorn_config.py'),
                gunicorn_config.app_name
            ),
            gunicorn_pidfile
        )
        # Downloader daemon
        downloader_pidfile = join(self.config['project_dir'], 'downloader.pid')
        file = join(self.config['project_dir'], 'src/daemons/downloader.py')
        self.__start_service(
            'File downloader daemon',
            '{file} --pidfile={0} --token={1} --downloads_dir={2} \
            start'.format(
                downloader_pidfile,
                self.config['telegram']['token'],
                self.config['downloads_dir'],
                file=file
            ),
            downloader_pidfile
        )
        # Dealer daemon
        dealer_pidfile = join(self.config['project_dir'], 'dealer.pid')
        file = join(self.config['project_dir'], 'src/daemons/dealer.py')
        self.__start_service(
            'Evernote dealer daemon',
            '{file} --pidfile={} start'.format(dealer_pidfile, file=file),
            dealer_pidfile
        )

    @cmd
    def stop(self):
        self.__stop_service('downloader')
        self.__stop_service('dealer')
        self.__stop_process('gunicorn', self.__get_pidfile('gunicorn'))

    @cmd
    def restart(self):
        self.stop()
        self.start()

    @cmd
    def reload(self):
        print('Reloading gunicorn... ', end="")
        pidfile = self.services['gunicorn']['pidfile']
        os.kill(get_pid(pidfile), signal.SIGHUP)
        print(green('OK'))

    @cmd
    def status(self):
        for service in self.services:
            print('{0}: '.format(service['name'].capitalize()), end="")
            if process_exists(service['pidfile']):
                print(green('Started'))
            else:
                print(red('Stopped'))
            print("\n")

    def set_webhook(self):
        from ext.telegram.api import BotApi
        telegram_api = BotApi(self.config['telegram']['token'])
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            telegram_api.setWebhook(self.config['telegram']['webhook_url'])
        )


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
