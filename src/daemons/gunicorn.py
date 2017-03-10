#!/usr/bin/env python3

import argparse
import os
import sys
import signal
from os.path import join
from os.path import realpath
from os.path import dirname

sys.path.append(dirname(realpath(dirname(__file__))))

import config.gunicorn as gunicorn_config
from config import config


def start(config_file, app_name):
    os.system('gunicorn --config={0} {1}'.format(config_file, app_name))


def stop(pidfile):
    if not os.path.exists(pidfile):
        print('pidfile %s does not exists. Daemon not running?' % pidfile)
        return
    with open(pidfile) as f:
        pid = int(f.read())
    os.kill(pid, signal.SIGTERM)
    os.unlink(pidfile)


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('CMD')
        args = parser.parse_args()
        cmd = args.CMD

        pidfile = join(config['project_dir'], 'gunicorn.pid')
        config_file = join(config['project_dir'], 'src/config/gunicorn.py')
        app_name = gunicorn_config.app_name

        if cmd == 'start':
            start(config_file, app_name)
        elif cmd == 'stop':
            stop(pidfile)
        elif cmd == 'restart':
            stop(pidfile)
            start(config_file, app_name)
        elif cmd == 'reload':
            with open(pidfile) as f:
                pid = int(f.read())
            os.kill(pid, signal.SIGHUP)
        else:
            print("Unknown command '{}'\n".format(cmd))
            sys.exit(1)
        print('OK')
    except Exception:
        print('FAILED')
        import traceback
        print(traceback.format_exc())
