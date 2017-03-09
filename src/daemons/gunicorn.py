#!/usr/bin/env python3

import argparse
import os
import sys
import signal


def start(args):
    os.system('gunicorn --config={0} {1}'.format(args.config, args.app))


def stop():
    with open(args.pidfile) as f:
        pid = int(f.read())
    os.kill(pid, signal.SIGTERM)
    os.unlink(args.pidfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pidfile', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--app', required=True)
    parser.add_argument('CMD')
    args = parser.parse_args()
    cmd = args.CMD

    if cmd == 'start':
        start(args)
    elif cmd == 'stop':
        stop()
    elif cmd == 'restart':
        stop()
        start()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)
