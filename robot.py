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


def green(text):
    if type(text) == bytes:
        text = text.decode()
    return "\033[92m%s\033[0m" % text


def red(text):
    if type(text) == bytes:
        text = text.decode()
    return "\033[91m%s\033[0m" % text


class ProcessOwner:
    def run(self, exec_path, *args):
        print('Running {}...'.format(basename(exec_path)), end='')
        process = subprocess.run([exec_path, *args],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        if process.returncode != 0:
            print(red('FAILED'))
            raise Exception(process.stdout.decode())
        print(green('OK'))

    def kill(self, pidfile, signal=signal.SIGTERM, message=None):
        if message is None:
            message = 'Killing {}...'.format(basename(pidfile))
        print(message, end='')
        if os.path.exists(pidfile):
            if self.process_exists(pidfile):
                with open(pidfile) as f:
                    pid = int(f.read())
                os.kill(pid, signal)
                if signal == signal.SIGTERM:
                    os.unlink(pidfile)
                print(green('OK'))
            else:
                print(red('FAILED'))
                print(red('Process {} not runnning'.format(pidfile)))
        else:
            print(green('OK'))

    def process_exists(self, pidfile):
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

    def daemon_start(self, daemon):
        print('Starting {}...'.format(basename(daemon.pidfile)))
        try:
            daemon.start()
            print(green('OK'))
        except Exception as e:
            print(red('FAILED'))
            raise e

    def daemon_stop(self, daemon):
        print('Stopping {}...'.format(basename(daemon.pidfile)), end='')
        try:
            daemon.stop()
            print(green('OK'))
        except Exception as e:
            print(red('FAILED'))
            raise e


class BotService(ProcessOwner):
    def __init__(self, config_file):
        sys.path.append(realpath(join(dirname(__file__), 'src')))
        config = importlib.import_module('config')
        self.config = config.config
        if config_file and not os.path.exists(config_file):
            config_dir = join(self.config['project_dir'], 'src/config')
            path = join(config_dir, config_file)
            if os.path.exists(path):
                config_file = path
        os.environ['EVERNOTEROBOT_CONFIG'] = config_file or ''
        self.gunicorn_pidfile = join(self.config['project_dir'], 'gunicorn.pid')

        dealer_module = importlib.import_module('bot.dealer')
        dealer_pidfile = join(self.config['project_dir'], 'dealer.pid')
        dealer_stdout = join(self.config['project_dir'], 'dealer.stdout.log')
        self.dealer_daemon = dealer_module.EvernoteDealerDaemon(dealer_pidfile, dealer_stdout)

    def start(self, use_gunicorn=False):
        os.makedirs(self.config['logs_dir'], mode=0o700, exist_ok=True)
        os.makedirs(self.config['downloads_dir'], mode=0o700, exist_ok=True)
        self.daemon_start(self.dealer_daemon)
        if use_gunicorn:
            import src.config.gunicorn as gunicorn_config
            config_file = join(self.config['project_dir'], 'src/config/gunicorn.py')
            app_name = gunicorn_config.app_name
            self.run('gunicorn', '--config={}'.format(config_file), app_name)
        else:
            from aiohttp import web
            from src.web.webapp import app
            web.run_app(app)

    def stop(self):
        self.daemon_stop(self.dealer_daemon)
        self.kill(self.gunicorn_pidfile, message='Stopping gunicorn...')

    def restart(self, use_gunicorn=False):
        self.stop()
        self.start(use_gunicorn)

    def reload(self):
        self.kill(self.gunicorn_pidfile, signal=signal.SIGHUP, message='Reloading gunicorn...')

    def status(self):
        for pidfile in [self.dealer_pidfile, self.gunicorn_pidfile]:
            print(green('STARTED') if self.process_exists(pidfile) else red('STOPPED'))

    def set_webhook(self):
        from ext.telegram.api import BotApi
        telegram_api = BotApi(self.config['telegram']['token'])
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            telegram_api.setWebhook(self.config['telegram']['webhook_url'])
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--gunicorn', action='store_true')
    parser.add_argument('CMD', help="Command (start/stop/reload/etc.)\n")
    args = parser.parse_args()
    cmd = args.CMD
    config_file = args.config
    use_gunicorn = args.gunicorn

    try:
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
    except Exception as e:
        print(red(e))
        sys.exit(1)

    print("Done.\n")
