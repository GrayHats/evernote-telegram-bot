#!/usr/bin/env python3

import argparse
import os
import sys
import signal
from os.path import join
from os.path import realpath
from os.path import dirname

sys.path.append(realpath(dirname(dirname(__file__))))

from config import config


def start(args):
    os.system('gunicorn --config={0} {1}'.format(args.config, args.app))


def stop(pidfile):
    if not os.path.exists(pidfile):
        print('pidfile %s does not exists. Daemon not running?' % pidfile)
        return
    with open(pidfile) as f:
        pid = int(f.read())
    os.kill(pid, signal.SIGTERM)
    os.unlink(pidfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--app')
    parser.add_argument('CMD')
    args = parser.parse_args()
    cmd = args.CMD
    pidfile = join(config['project_dir'], 'gunicorn.pid')

    if cmd == 'start':
        assert args.config
        assert args.app
        start(args)
    elif cmd == 'stop':
        stop(pidfile)
    elif cmd == 'restart':
        stop()
        start()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)
