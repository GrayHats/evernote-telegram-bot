import sys
import logging.config
import os
from os.path import realpath, dirname
from importlib.util import spec_from_file_location, module_from_spec

import aiohttp.web
import aiohttp_jinja2
import jinja2


sys.path.insert(0, realpath(dirname(dirname(__file__))))

import settings
from bot import EvernoteBot


def get_module_info(module_name):
    base_dir = realpath(dirname(__file__))
    specials = {
        'url_scheme': 'urls',
        'middlewares': 'middlewares',
    }
    info = {}
    for key, special_name in specials.items():
        file_path = '{0}/{1}/{2}.py'.format(base_dir, module_name, special_name)
        if os.path.exists(file_path):
            spec = spec_from_file_location(module_name, file_path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            info[special_name] = getattr(module, special_name)
    info['template_path'] = '{0}/{1}/html'.format(base_dir, module_name)
    return info


modules = [
    'admin',
    'bot',
]

loaded_modules = [get_module_info(m) for m in modules]

middlewares = []
for m in loaded_modules:
    if m.get('middlewares'):
        middlewares.extend(m['middlewares'])

app = aiohttp.web.Application(middlewares=middlewares)
template_path_list = []
for module_info in loaded_modules:
    if module_info.get('template_path'):
        template_path_list.append(module_info['template_path'])
    if module_info.get('url_scheme'):
        for url_scheme in module_info['url_scheme']:
            app.router.add_route(*url_scheme)

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path_list))
logging.config.dictConfig(settings.LOG_SETTINGS)
app.logger = logging.getLogger('bot')
bot = EvernoteBot(settings.TELEGRAM['token'], 'evernoterobot')
app.bot = bot
