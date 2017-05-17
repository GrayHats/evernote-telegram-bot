import sys
import os
from os.path import realpath
from os.path import dirname
from os.path import join
from os.path import exists
import yaml


def merge_configs(dict1, dict2):
    if dict1 is None:
        dict1 = {}
    for k, v in dict2.items():
        if isinstance(v, dict):
            dict1[k] = merge_configs(dict1.get(k), v)
        else:
            dict1[k] = v
    return dict1


config_file = realpath(join(dirname(__file__), 'config.yaml'))
with open(config_file) as f:
    config = yaml.load(f.read())

additional_config_file = os.environ.get('EVERNOTEROBOT_CONFIG')
if additional_config_file and exists(additional_config_file):
    with open(additional_config_file) as f:
        additional_config = yaml.load(f.read())
        if additional_config:
            config = merge_configs(config, additional_config)

src_dir = realpath(dirname(dirname(__file__)))
sys.path.append(src_dir)
project_dir = realpath(dirname(src_dir))
config['project_dir'] = project_dir
config['logs_dir'] = join(project_dir, 'logs')
config['downloads_dir'] = join(project_dir, 'downloads')

if not os.path.exists(config['logs_dir']):
    os.makedirs(config['logs_dir'], mode=0o700, exist_ok=True)
if not os.path.exists(config['downloads_dir']):
    os.makedirs(config['downloads_dir'], mode=0o700, exist_ok=True)
