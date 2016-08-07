import argparse
import sys
import logging.config
from os.path import dirname, realpath, join

sys.path.insert(0, realpath(dirname(__file__)))

from daemons.dealer import EvernoteDealerDaemon
import settings

logging.config.dictConfig(settings.LOG_SETTINGS)


def dealer_pidfile():
    return join(realpath(dirname(__file__)), 'dealer.pid')


def dealer_start():
    print('Starting dealer...')
    EvernoteDealerDaemon(dealer_pidfile()).start()


def dealer_stop():
    print('Stopping dealer...')
    EvernoteDealerDaemon(dealer_pidfile()).stop()


def start():
    dealer_start()


def stop():
    dealer_stop()


if __name__ == "__main__":
    command_handlers = {
        'start': start,
        'stop': stop,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('CMD', help="Available commands:\n{0}".format(
        "|".join([cmd for cmd in command_handlers.keys()])
    ))
    args = parser.parse_args()
    func = command_handlers.get(args.CMD)
    if not func:
        print("Unknown command '%s'" % args.CMD)
        sys.exit(1)
    func()
    print('Done.')
