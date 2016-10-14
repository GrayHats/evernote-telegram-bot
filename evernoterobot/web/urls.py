import settings
from web.dashboard import login, list_downloads, dashboard, list_failed_updates, \
    list_updates, list_users, view_telegram_update_logs, fix_failed_update

dashboard_url = lambda url=None: '{0}{1}'.format(settings.DASHBOARD['root_url'], url or '')

dashboard_urls = [
    ('GET', dashboard_url(), login),
    ('GET', dashboard_url('/dashboard'), dashboard),
    ('GET', dashboard_url('/downloads'), list_downloads),
    ('GET', dashboard_url('/failed_updates'), list_failed_updates),
    ('GET', dashboard_url('/queue'), list_updates),
    ('GET', dashboard_url('/users'), list_users),
    ('GET', dashboard_url('/logs'), view_telegram_update_logs),
    ('POST', dashboard_url('/fix_failed_update'), fix_failed_update),
]
