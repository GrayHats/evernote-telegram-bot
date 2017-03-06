#!/usr/bin/env python3

import sys
import argparse
from os.path import dirname
from os.path import realpath

sys.path.append(realpath(dirname(dirname(__file__))))

from bot.dealer import EvernoteDealer
from daemons.daemon import Daemon


class EvernoteDealerDaemon(Daemon):

    def run(self):
        dealer = EvernoteDealer()
        dealer.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pidfile', required=True)
    parser.add_argument('CMD')
    args = parser.parse_args()
    cmd = args.CMD

    daemon = EvernoteDealerDaemon(args.pidfile)
    if cmd == 'start':
        daemon.start()
    elif cmd == 'stop':
        daemon.stop()
    elif cmd == 'restart':
        daemon.restart()
    else:
        print("Unknown command '{}'\n".format(cmd))
        sys.exit(1)
