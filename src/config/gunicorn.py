import sys
import multiprocessing
import importlib
from os.path import join
from os.path import dirname
from os.path import realpath

src_dir = realpath(dirname(dirname(__file__)))
sys.path.append(src_dir)
config_data = importlib.import_module('config').config

bind = '127.0.0.1:{}'.format(config_data['gunicorn']['port'])
backlog = 128
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'aiohttp.worker.GunicornWebWorker'
pidfile = join(config_data['project_dir'], 'gunicorn.pid')
accesslog = join(config_data['logs_dir'], 'gunicorn.access.log')
errorlog = join(config_data['logs_dir'], 'gunicorn.error.log')
loglevel = 'info'
app_name = 'web.webapp:app'
access_log_format = '%a %l %u %t "%r" %s %b "%{Referrer}i" "%{User-Agent}i"'
daemon = True
