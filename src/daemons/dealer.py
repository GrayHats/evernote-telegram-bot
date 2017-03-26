#!/usr/bin/env python3

import sys
import argparse
from os.path import dirname
from os.path import realpath
from os.path import join

sys.path.append(dirname(realpath(dirname(__file__))))

from bot.dealer import EvernoteDealer
from daemons.daemon import Daemon
from config import config


class EvernoteDealerDaemon(Daemon):

    def run(self):
        dealer = EvernoteDealer()
        dealer.run()


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('CMD')
        args = parser.parse_args()
        cmd = args.CMD

        pidfile = join(config['project_dir'], 'dealer.pid')
        stdout = join(config['project_dir'], 'dealer.stdout.log')
        daemon = EvernoteDealerDaemon(pidfile, stdout)
        if cmd == 'start':
            daemon.start()
        elif cmd == 'stop':
            daemon.stop()
        elif cmd == 'restart':
            daemon.restart()
        else:
            print("Unknown command '{}'\n".format(cmd))
            sys.exit(1)
        print('OK')
    except Exception:
        print('FAILED')
        import traceback
        print(traceback.format_exc())
