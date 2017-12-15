#!/usr/bin/env python3

import argparse
import sys
import os
import signal
import asyncio
import importlib
import subprocess
from os.path import join
from os.path import dirname
from os.path import basename
from os.path import realpath

import aiohttp.web

sys.path.append(join(realpath(dirname(__file__)), 'src'))

from config import config
from utils.daemon import Daemon
from ext.telegram.api import BotApi
from bot.dealer import EvernoteDealerDaemon


def green(text):
    if type(text) == bytes:
        text = text.decode()
    return "\033[92m%s\033[0m" % text


def red(text):
    if type(text) == bytes:
        text = text.decode()
    return "\033[91m%s\033[0m" % text


class BotDaemon(Daemon):
    def run(self):
        from web.webapp import app
        aiohttp.web.run_app(app, port=config['port'])


class BotService:
    def __init__(self, config):
        self.config = config
        self.dealer_daemon = self.create_daemon('dealer', EvernoteDealerDaemon)
        self.bot_daemon = self.create_daemon('bot', BotDaemon)

    def create_daemon(self, name, class_object):
        project_dir = self.config['project_dir']
        pidfile = join(project_dir, '{}.pid'.format(name))
        stdout_filename = join(self.config['logs_dir'], '{}.stdout.log'.format(name))
        return class_object(pidfile, stdout_filename)

    def start(self):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)
        self.dealer_daemon.start()
        self.bot_daemon.start()
        print(green('OK\n'))

    def stop(self):
        self.dealer_daemon.stop()
        self.bot_daemon.stop()
        print(green('OK\n'))

    def restart(self):
        self.stop()
        self.start()

    def set_webhook(self):
        telegram_config = self.config['telegram']
        api = BotApi(telegram_config['token'])
        loop = asyncio.get_event_loop()
        url = telegram_config['webhook_url']
        loop.run_until_complete(api.setWebhook(url))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('CMD', help='Command (start/stop/restart)\n')
    args = parser.parse_args()
    cmd = args.CMD
    try:
        service = BotService(config)
        if cmd == 'start':
            service.start()
        elif cmd == 'stop':
            service.stop()
        elif cmd == 'restart':
            service.restart()
        elif cmd == 'set_webhook':
            service.set_webhook()
        else:
            print('Unknown command "{}"\n'.format(cmd))
            sys.exit(1)
    except Exception as e:
        print(red(e))
        sys.exit(1)