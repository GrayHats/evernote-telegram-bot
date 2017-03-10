import os
import logging.config
from os.path import realpath
from os.path import dirname
from importlib.util import spec_from_file_location
from importlib.util import module_from_spec

import jinja2
import aiohttp_jinja2
import aiohttp.web

from bot import EvernoteBot
from config import config
from utils.logs import get_config


def get_module_info(module_name):
    base_dir = realpath(dirname(__file__))
    specials = {
        'url_scheme': 'urls',
        'middlewares': 'middlewares',
    }
    info = {}
    for key, special_name in specials.items():
        path = '{0}/{1}/{2}.py'.format(base_dir, module_name, special_name)
        if os.path.exists(path):
            spec = spec_from_file_location(module_name, path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            info[special_name] = getattr(module, special_name)
    template_dir = '{0}/{1}/html'.format(base_dir, module_name)
    if os.path.exists(template_dir):
        info['template_path'] = template_dir
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
    if module_info.get('urls'):
        for url_scheme in module_info['urls']:
            app.router.add_route(*url_scheme)

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path_list))
log_config = get_config(
    config['project_name'], config['logs_dir'], config.get('smtp')
)
logging.config.dictConfig(log_config)
app.logger = logging.getLogger('bot')
bot = EvernoteBot(config['telegram']['token'], 'evernoterobot')
bot.config = config  # FIXME:
app.bot = bot
