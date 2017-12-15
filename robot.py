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
    def __init__(self):
        self.config = config

        project_dir = self.config['project_dir']
        dealer_pidfile = join(project_dir, 'dealer.pid')
        dealer_stdout = join(project_dir, 'dealer.stdout.log')
        self.dealer_daemon = EvernoteDealerDaemon(dealer_pidfile, dealer_stdout)

        bot_pidfile = join(project_dir, 'bot.pid')
        bot_stdout = join(project_dir, 'bot.stdout.log')
        self.bot_daemon = BotDaemon(bot_pidfile, bot_stdout)

    def start(self):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)
        self.daemon_start(self.dealer_daemon)
        self.daemon_start(self.bot_daemon)

    def daemon_start(self, daemon):
        print('Starting {}...'.format(basename(daemon.pidfile)))
        try:
            daemon.start()
            print(green('OK'))
        except Exception as e:
            print(red('FAILED'))
            raise e

    def stop(self):
        self.daemon_stop(self.dealer_daemon)
        self.daemon_stop(self.bot_daemon)

    def daemon_stop(self, daemon):
        print('Stopping {}...'.format(basename(daemon.pidfile)), end='')
        try:
            daemon.stop()
            print(green('OK'))
        except Exception as e:
            print(red('FAILED'))
            raise e

    def restart(self):
        self.stop()
        self.start()

    def set_webhook(self):
        from ext.telegram.api import BotApi
        telegram_api = BotApi(self.config['telegram']['token'])
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            telegram_api.setWebhook(self.config['telegram']['webhook_url'])
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('CMD', help="Command (start/stop/restart)\n")
    args = parser.parse_args()
    cmd = args.CMD
    try:
        service = BotService()
        if cmd == 'start':
            service.start()
        elif cmd == 'stop':
            service.stop()
        elif cmd == 'restart':
            service.restart()
        elif cmd == 'set_webhook':
            service.set_webhook()
        else:
            print("Unknown command '{}'\n".format(cmd))
            sys.exit(1)
    except Exception as e:
        print(red(e))
        sys.exit(1)

    print("Done.\n")
