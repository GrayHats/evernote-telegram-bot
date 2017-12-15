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


config_dir = realpath(dirname(__file__))
config_file = join(config_dir, 'config.yaml')
with open(config_file) as f:
    config = yaml.load(f.read())

local_config_file = join(config_dir, 'local.yaml')
if local_config_file and exists(local_config_file):
    with open(local_config_file) as f:
        local_config = yaml.load(f.read())
        if local_config:
            config = merge_configs(config, local_config)

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
