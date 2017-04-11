#!/usr/bin/env python3

import argparse
import sys
import os
import asyncio
import importlib
from os.path import join
from os.path import basename


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
        config = importlib.import_module('src.config')
        self.config = config.config
        if config_file and not os.path.exists(config_file):
            config_dir = join(self.config['project_dir'], 'src/config')
            path = join(config_dir, config_file)
            if os.path.exists(path):
                config_file = path
        os.environ['EVERNOTEROBOT_CONFIG'] = config_file or ''
        daemons_dir = join(self.config['project_dir'], 'src/daemons')
        self.dealer = join(daemons_dir, 'dealer.py')
        self.gunicorn = join(daemons_dir, 'gunicorn.py')

    @cmd
    def start(self, use_gunicorn=False):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)

        print('Starting dealer...')
        os.system('{file} start'.format(file=self.dealer))
        if use_gunicorn:
            print('Starting gunicorn...')
            os.system('{file} start'.format(file=self.gunicorn))
        else:
            # import here because there are import config that reads file.
            # Some little optimization
            from aiohttp import web
            from src.web.webapp import app
            web.run_app(app)

    @cmd
    def stop(self):
        services = [self.dealer, self.gunicorn]
        for filename in services:
            print('Stopping {}'.format(basename(filename)))
            os.system('{file} stop'.format(file=filename))

    @cmd
    def restart(self, use_gunicorn=False):
        self.stop()
        self.start(use_gunicorn)

    @cmd
    def reload(self):
        os.system('{file} reload'.format(file=self.gunicorn))

    @cmd
    def status(self):
        services = [self.dealer, self.gunicorn]
        for filename in services:
            os.system('{file} status'.format(file=filename))

    @cmd
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
        service.restart(use_gunicorn)
    elif cmd == 'reload':
        service.reload()
    elif cmd == 'status':
        service.status()
    elif cmd == 'set_webhook':
        service.set_webhook()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)

    print("Done.\n")
