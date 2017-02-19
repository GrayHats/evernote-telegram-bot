from web.admin.handlers import login
from web.admin.handlers import logout
from web.admin.handlers import list_downloads
from web.admin.handlers import dashboard
from web.admin.handlers import list_failed_updates
from web.admin.handlers import list_updates
from web.admin.handlers import list_users
from web.admin.handlers import view_telegram_update_logs
from web.admin.handlers import fix_failed_update
from web.admin.handlers import admin_url


no_auth_urls = [
    ('GET', admin_url(), login),
    ('POST', admin_url(), login),
]

auth_required_urls = [
    ('GET', admin_url('/logout'), logout),
    ('GET', admin_url('/dashboard'), dashboard),
    ('GET', admin_url('/downloads'), list_downloads),
    ('GET', admin_url('/failed_updates'), list_failed_updates),
    ('GET', admin_url('/queue'), list_updates),
    ('GET', admin_url('/users'), list_users),
    ('GET', admin_url('/logs'), view_telegram_update_logs),
    ('POST', admin_url('/fix_failed_update'), fix_failed_update),
]

urls = []
for method, url, handler in auth_required_urls:
    setattr(handler, 'auth_required', True)
    urls.append((method, url, handler))

urls += no_auth_urls
