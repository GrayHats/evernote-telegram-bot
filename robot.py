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


class Service:

    def __init__(self, config, name, exec_file):
        self.name = name
        self.exec_file = exec_file
        self.config = config
        self.pidfile = join(config['project_dir'], '{}.pid'.format(name))

    def start(self, options):
        options = ' '.join(
            ['{0}={1}'.format(k, v) for k, v in options.items()]
        )
        cmd = '{exec_file} {options} start'.format(
            exec_file=self.exec_file,
            options=options
        )
        print('Starting {}'.format(self.name), end="")
        os.system(cmd)
        time.sleep(1)
        if process_exists(self.pidfile):
            print(green('OK'))
        else:
            print(red('FAILED'))

    def stop(self):
        cmd = '{file} --pidfile={pidfile} stop'.format(
            file=self.exec_file,
            pidfile=self.pidfile
        )
        print('Stopping {}'.format(self.name), end="")
        os.system(cmd)
        time.sleep(1)
        if not process_exists(self.pidfile):
            print(green('OK'))
        else:
            print(red('FAILED'))


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
        os.environ['EVERNOTEROBOT_CONFIG'] = config_file or ''
        config = importlib.import_module('src.config')
        self.config = config.config
        log_config = get_config(
            self.config['project_name'],
            self.config['logs_dir'],
            self.config.get('smtp')
        )
        logging.config.dictConfig(log_config)
        self.dealer = Service(
            self.config,
            'dealer',
            join(self.config['project_dir'], 'src/daemons/dealer.py')
        )
        self.downloader = Service(
            self.config,
            'downloader',
            join(self.config['project_dir'], 'src/daemons/downloader.py')
        )
        self.gunicorn = Service(self.config, 'gunicorn', 'gunicorn')

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

        import gunicorn_config
        config_path = join(
            self.config['project_dir'], 'src/gunicorn_config.py'
        )
        self.gunicorn.start({
            '--config': config_path,
            '--app': gunicorn_config.app_name,
        })
        self.downloader.start({
            '--token': self.config['telegram']['token'],
            '--downloads_dir': join(self.config['project_dir'], 'downloads')
        })
        self.dealer.start({})

    @cmd
    def stop(self):
        self.downloader.stop()
        self.dealer.stop()
        self.gunicorn.stop()

    @cmd
    def restart(self):
        self.stop()
        self.start()

    @cmd
    def reload(self):
        print('Reloading gunicorn... ', end="")
        os.kill(get_pid(self.gunicorn.pidfile), signal.SIGHUP)
        print(green('OK'))

    @cmd
    def status(self):
        services = [self.dealer, self.downloader, self.gunicorn]
        for service in services:
            print('{0}: '.format(service.name.capitalize()), end="")
            if process_exists(service.pidfile):
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
