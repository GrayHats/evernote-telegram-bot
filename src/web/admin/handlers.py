import time
import datetime
import hashlib
from bson import ObjectId
import aiohttp_jinja2
from aiohttp import web

from bot.model import FailedUpdate
from bot.model import TelegramUpdate
from bot.model import User
from bot.model import TelegramUpdateLog
from config import config
from web import cookies


def admin_url(url=None):
    return '/admin{0}'.format(url or '')


def get_hash(s):
    m = hashlib.sha1()
    m.update(s.encode())
    return m.hexdigest()


def get_login(request):
    if request.cookies and request.cookies['evernoterobot']:
        data = cookies.decode(
            request.cookies['evernoterobot'],
            key=config['secret_key']
        )
        username = data.get('login')
        if filter(lambda x: x['login'] == username, config['admins']):
            now = time.time()
            if data.get('expire_time', now) >= now:
                return username


async def login(request):
    if request.method == 'GET':
        if get_login(request):
            url = request.headers.get('REFERER', admin_url('/dashboard'))
            return web.HTTPFound(url)
        params = {'admin_url': admin_url()}
        return aiohttp_jinja2.render_template('login.html', request, params)
    try:
        await request.post()
        login = request.POST.get('login')
        password = request.POST.get('password')
        admins = config['admins']
        if login and password:
            for user in admins:
                if login == user['login'] and password == user['password']:
                    response = web.HTTPFound(admin_url('/dashboard'))
                    response.set_cookie(
                        'evernoterobot',
                        cookies.encode({
                            'login': login,
                            'expire_time': time.time() + 3600 * 24,
                        }, key=config['secret_key'])
                    )
                    return response
            params = {'error': 'Invalid login or password'}
            return aiohttp_jinja2.render_template(
                'login.html', request, params)
        return aiohttp_jinja2.render_template('login.html', request, {})
    except Exception as e:
        request.app.logger.error(e, exc_info=1)
        params = {'error': 'Access denied', 'admin_url': admin_url()}
        return aiohttp_jinja2.render_template('login.html', request, params)


async def logout(request):
    response = web.HTTPFound(admin_url())
    response.del_cookie('evernoterobot')
    return response


async def dashboard(request):
    params = {'cnt_failed_updates': len(FailedUpdate.find())}
    return aiohttp_jinja2.render_template('dashboard.html', request, params)


async def list_downloads(request):
    # TODO:
    params = {'list_downloads': []}
    response = aiohttp_jinja2.render_template('downloads.html', request,
                                              params)
    return response


async def list_failed_updates(request):
    failed_updates = [update.save_data() for update in FailedUpdate.find()]
    params = {'failed_updates': failed_updates}
    response = aiohttp_jinja2.render_template('failed_updates.html', request,
                                              params)
    return response


async def list_updates(request):
    updates = [update.save_data() for update in TelegramUpdate.find()]
    params = {'queue': updates}
    response = aiohttp_jinja2.render_template('queue.html', request, params)
    return response


async def fix_failed_update(request):
    await request.post()
    update_id = request.POST.get('update_id')
    if update_id:
        updates = [FailedUpdate.get({'id': ObjectId(update_id)})]
    elif not update_id and request.POST.get('all'):
        updates = FailedUpdate.find()
    else:
        updates = []
    for failed_update in updates:
        await request.app.bot.handle_update({
            'update_id': failed_update.id,
            'message': failed_update.message
        })
        failed_update.delete()
    return await list_failed_updates(request)


async def list_users(request):
    page = request.GET.get('page', 0)
    page_size = 50
    total_cnt = User.count()
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)
    weekly_active = User.count({'last_request_time': {'$gte': week_ago}})
    monthly_active = User.count({'last_request_time': {'$gte': month_ago}})
    num_pages = total_cnt / page_size + 1
    all_users = User.find({}, skip=page*page_size, limit=page_size,
                          sort=[('last_request_time', -1)])
    users = [x for x in all_users]
    return aiohttp_jinja2.render_template(
        'users.html',
        request,
        {
            'users': users,
            'num_pages': num_pages,
            'total': total_cnt,
            'monthly_active': monthly_active,
            'weekly_active': weekly_active,
        }
    )


def dict_get(d: dict, *keys):
    if not keys:
        return d
    value = d
    for k in keys:
        value = value.get(k)
        if not value:
            return
    return value


async def view_telegram_update_logs(request):
    page = request.GET.get('page', 0)
    page_size = 50
    total_cnt = TelegramUpdateLog.count()
    num_pages = total_cnt / page_size + 1
    logs = []
    updates = TelegramUpdateLog.find({}, skip=page*page_size, limit=page_size,
                                     sort=[('created', -1)])
    for entry in updates:
        update = entry.update
        if not update.get('message') and update.get('edited_message'):
            update['message'] = update['edited_message']
            del update['edited_message']
        logs.append({
            'created': entry.created,
            'from_id': dict_get(update, 'message', 'from', 'id'),
            'first_name': dict_get(update, 'message', 'from', 'first_name'),
            'last_name': dict_get(update, 'message', 'from', 'last_name'),
            'data': str(update),
            'headers': entry.headers,
        })
    return aiohttp_jinja2.render_template(
        'logs.html',
        request,
        {'logs': logs, 'num_pages': num_pages}
    )
