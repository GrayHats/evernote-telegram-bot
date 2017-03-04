from config import config
from web.bot.telegram import handle_update
from web.bot.evernote import oauth_callback, oauth_callback_full_access


urls = [
    ('POST', '/{}'.format(config['telegram']['token']), handle_update),
    ('GET', '/evernote/oauth', oauth_callback),
    ('GET', '/evernote/oauth/full_access', oauth_callback_full_access),
]
