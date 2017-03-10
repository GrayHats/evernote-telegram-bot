import multiprocessing
from os.path import join

import config

bind = '127.0.0.1:{}'.format(config['gunicorn']['port'])
backlog = 128
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'aiohttp.worker.GunicornWebWorker'
pidfile = join(config['project_dir'], '{}.pid'.format(config['project_name']))
accesslog = join(config['logs_dir'], 'gunicorn.log')
errorlog = join(config['logs_dir'], 'gunicorn.log')
loglevel = 'info'
app_name = 'web.webapp:app'
access_log_format = '%a %l %u %t "%r" %s %b "%{Referrer}i" "%{User-Agent}i"'
daemon = True

# Run this command to start gunicorn
# $ gunicorn --config gunicorn_config.py webapp:app
