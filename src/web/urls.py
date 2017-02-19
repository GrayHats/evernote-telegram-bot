import settings
from web.telegram import handle_update
from web.evernote import oauth_callback, oauth_callback_full_access


url_scheme = [
    ('POST', '/{}'.format(settings.TELEGRAM['token']), handle_update),
    ('GET', '/evernote/oauth', oauth_callback),
    ('GET', '/evernote/oauth/full_access', oauth_callback_full_access),
]
