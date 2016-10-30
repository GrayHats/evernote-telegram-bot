from aiohttp import web
import aiohttp_jinja2
from bson import ObjectId

from bot import DownloadTask
from bot.model import FailedUpdate, TelegramUpdate, User, TelegramUpdateLog
from settings import SECRET, DASHBOARD, ADMINS
import hashlib

from web import cookies


def get_hash(s):
    m = hashlib.sha1()
    m.update(s.encode())
    return m.hexdigest()


def get_login(request):
    if request.cookies and request.cookies['evernoterobot']:
        data = cookies.decode(request.cookies['evernoterobot'])
        username = data.get('login')
        if filter(lambda x: x['login'] == username, ADMINS):
            # TODO: check expire_time
            # TODO: renew expire_time
            return username


async def login(request):
    if request.method == 'GET':
        if get_login(request):
            return web.HTTPFound('{0}{1}'.format(DASHBOARD['root_url'], '/dashboard'))
        return aiohttp_jinja2.render_template('login.html', request, {})
    try:
        await request.post()
        login = request.POST.get('login')
        password = request.POST.get('password')
        admins = SECRET['admins']
        if login and password:
            login = get_hash(login)
            password = get_hash(password)
            for user in admins:
                if login == user['login'] and password == user['password']:
                    response = web.HTTPFound(DASHBOARD['root_url'])
                    response.set_cookie('evernoterobot', cookies.encode({'login': login})) # TODO: set expire_time
                    return response
            return aiohttp_jinja2.render_template('login.html', request,
                                                  {'error': 'Invalid login or password'})
        return aiohttp_jinja2.render_template('login.html', request, {})
    except Exception as e:
        request.app.logger.error(e, exc_info=1)
        return aiohttp_jinja2.render_template('login.html', request,
                                              { 'error': 'Access denied' })


async def logout(request):
    response = web.HTTPFound(DASHBOARD['root_url'])
    response.del_cookie('evernoterobot')
    return response


async def dashboard(request):
    return aiohttp_jinja2.render_template('dashboard.html', request,
                                          {
                                              'cnt_failed_updates': len(FailedUpdate.find()),
                                          })


async def list_downloads(request):
    downloads = [task.save_data() for task in DownloadTask.find()]
    response = aiohttp_jinja2.render_template('downloads.html',
                                              request,
                                              {
                                                  'list_downloads': downloads
                                              })
    return response


async def list_failed_updates(request):
    failed_updates = [update.save_data() for update in FailedUpdate.find()]
    response = aiohttp_jinja2.render_template('failed_updates.html',
                                              request,
                                              {
                                                  'failed_updates': failed_updates
                                              })
    return response


async def list_updates(request):
    updates = [update.save_data() for update in TelegramUpdate.find()]
    response = aiohttp_jinja2.render_template('queue.html',
                                              request,
                                              {
                                                  'queue': updates,
                                              })
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
        await request.app.bot.handle_update({ 'update_id': failed_update.id, 'message': failed_update.message })
        failed_update.delete()
    return await list_failed_updates(request)


async def list_users(request):
    page = request.GET.get('page', 0)
    page_size = 50
    total_cnt = User.count()
    num_pages = total_cnt / page_size + 1
    users = [x for x in User.find({}, skip=page*page_size, limit=page_size, sort=[('last_request_time', -1)])]
    return aiohttp_jinja2.render_template(
        'users.html',
        request,
        {
            'users': users,
            'num_pages': num_pages,
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
    for entry in TelegramUpdateLog.find({}, skip=page*page_size, limit=page_size, sort=[('created', -1)]):
        if not entry.update.get('message') and entry.update.get('edited_message'):
            entry.update['message'] = entry.update['edited_message']
            del entry.update['edited_message']
        entry = entry.to_dict()
        logs.append({
            'created': entry.get('created'),
            'from_id': dict_get(entry, 'message', 'from', 'id'),
            'first_name': dict_get(entry, 'message', 'from', 'first_name'),
            'last_name': dict_get(entry, 'message', 'from', 'last_name'),
            'update': entry.get('update'),
            'headers': entry.get('headers') or {},
        })
    return aiohttp_jinja2.render_template(
        'logs.html',
        request,
        {
            'logs': logs,
            'num_pages': num_pages,
        }
    )
