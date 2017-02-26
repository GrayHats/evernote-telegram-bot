import os
from os.path import dirname, join, realpath
import json


DEBUG = True

PROJECT_NAME = 'evernoterobot'
# TODO: переименовать в PROJECT_ROOT
PROJECT_DIR = realpath(dirname(dirname(__file__)))
ROOT_DIR = realpath(dirname(PROJECT_DIR))
LOGS_DIR = join(realpath(ROOT_DIR), 'logs')
DOWNLOADS_DIR = join(realpath(ROOT_DIR), 'downloads')

os.makedirs(LOGS_DIR, mode=0o700, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, mode=0o700, exist_ok=True)

secret_file = join(PROJECT_DIR, 'settings/secret.json')
if not os.path.exists(secret_file):
    raise FileNotFoundError(secret_file)
with open(join(PROJECT_DIR, secret_file)) as f:
    SECRET = json.load(f)

SMTP = SECRET['smtp']
ADMINS = SECRET['admins']

STORAGE = {
    'class': 'bot.storage.MongoStorage',
    'host': 'localhost',
    'port': 27017,
    'db': 'evernoterobot',
}

MEMCACHED = {
    'host': '127.0.0.1',
    'port': 11211,
}
