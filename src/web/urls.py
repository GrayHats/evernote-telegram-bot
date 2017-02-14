import settings
from web.telegram import handle_update
from web.evernote import oauth_callback, oauth_callback_full_access
from web.dashboard import login, logout, list_downloads, dashboard, list_failed_updates, \
    list_updates, list_users, view_telegram_update_logs, fix_failed_update


def admin_url(url=None):
    return '/admin{0}'.format(url or '/')


def auth_required(func):
    setattr(func, 'auth_required', False)
    return func


url_scheme = [
    ('POST', '/{}'.format(settings.TELEGRAM['token']), handle_update),

    ('GET', '/evernote/oauth', oauth_callback),
    ('GET', '/evernote/oauth/full_access', oauth_callback_full_access),

    ('GET', admin_url(), login),
    ('POST', admin_url(), login),
    ('GET', admin_url('/logout'), auth_required(logout)),
    ('GET', admin_url('/dashboard'), auth_required(dashboard)),
    ('GET', admin_url('/downloads'), auth_required(list_downloads)),
    ('GET', admin_url('/failed_updates'), auth_required(list_failed_updates)),
    ('GET', admin_url('/queue'), auth_required(list_updates)),
    ('GET', admin_url('/users'), auth_required(list_users)),
    ('GET', admin_url('/logs'), auth_required(view_telegram_update_logs)),
    ('POST', admin_url('/fix_failed_update'), auth_required(fix_failed_update)),
]
