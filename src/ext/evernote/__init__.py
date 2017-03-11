import sys
from os.path import dirname
from os.path import realpath
from os.path import join

path = join(realpath(dirname(__file__)), 'evernote-sdk-python3/lib')
sys.path.insert(0, path)

from evernote.api.client import EvernoteClient as EvernoteSdk
