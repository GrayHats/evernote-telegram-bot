from .base import *

TELEGRAM = SECRET['telegram']['dev']
EVERNOTE = SECRET['evernote']['dev']

STORAGE = {
    'class': 'bot.storage.MemoryStorage',
}
