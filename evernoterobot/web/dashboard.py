from aiohttp import web
import aiohttp_jinja2
from bson import ObjectId

from bot import DownloadTask
from bot.model import FailedUpdate, TelegramUpdate, User, TelegramUpdateLog
from settings import SECRET
import hashlib


def get_hash(s):
    m = hashlib.sha1()
    m.update(s.encode())
    return m.hexdigest()


async def login(request):
    try:
        login = request.GET.get('login')
        password = request.GET.get('password')
        admins = SECRET['admins']
        if login and password:
            login = get_hash(login)
            password = get_hash(password)
            for user in admins:
                if login == user['login'] and password == user['password']:
                    return web.HTTPFound('/a/dashboard/{0}'.format(SECRET['secret_key']))
            return aiohttp_jinja2.render_template('login.html', request,
                                                  {'error': 'Invalid login or password'})
        return aiohttp_jinja2.render_template('login.html', request, {})
    except Exception as e:
        request.app.logger.error(e, exc_info=1)
        return aiohttp_jinja2.render_template('login.html', request,
                                              { 'error': 'Access denied' })


async def dashboard(request):
    return aiohttp_jinja2.render_template('dashboard.html', request,
                                          {
                                              'secret': SECRET['secret_key'],
                                              'cnt_failed_updates': len(FailedUpdate.find()),
                                          })


async def list_downloads(request):
    downloads = [task.save_data() for task in DownloadTask.find()]
    response = aiohttp_jinja2.render_template('downloads.html',
                                              request,
                                              {
                                                  'secret': SECRET['secret_key'],
                                                  'list_downloads': downloads
                                              })
    return response


async def list_failed_updates(request):
    failed_updates = [update.save_data() for update in FailedUpdate.find()]
    response = aiohttp_jinja2.render_template('failed_updates.html',
                                              request,
                                              {
                                                  'secret': SECRET['secret_key'],
                                                  'failed_updates': failed_updates
                                              })
    return response


async def list_updates(request):
    updates = [update.save_data() for update in TelegramUpdate.find()]
    response = aiohttp_jinja2.render_template('queue.html',
                                              request,
                                              {
                                                  'secret': SECRET['secret_key'],
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
    users = [x for x in User.find({}, skip=page*page_size, limit=page_size)]
    return aiohttp_jinja2.render_template(
        'users.html',
        request,
        {
            'secret': SECRET['secret_key'],
            'users': users,
            'num_pages': num_pages,
        }
    )


async def view_telegram_update_logs(request):
    page = request.GET.get('page', 0)
    page_size = 50
    total_cnt = TelegramUpdateLog.count()
    num_pages = total_cnt / page_size + 1
    logs = [x for x in TelegramUpdateLog.find({}, skip=page*page_size, limit=page_size, sort=[('created', -1)])]
    return aiohttp_jinja2.render_template(
        'logs.html',
        request,
        {
            'secret': SECRET['secret_key'],
            'logs': logs,
            'num_pages': num_pages,
        }
    )
