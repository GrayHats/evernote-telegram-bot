from .base import *

DEBUG = False

TELEGRAM = SECRET['telegram']['live']
EVERNOTE = SECRET['evernote']['live']

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
