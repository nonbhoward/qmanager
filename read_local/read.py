# imports, python
import os
from pathlib import Path

# imports, third-party
import yaml

# imports, project
from hardcode.hardcode import Hardcode


def read_config():
    # init core objects
    project_name = Hardcode.project_name

    # get path
    path_to_config = Hardcode.path_to_config

    # verify
    if not os.path.exists(path_to_config):
        print(f'path not exist : {path_to_config}')
        exit()

    # open and read
    with open(path_to_config, 'r') as config_r:
        config_contents = config_r.read()
        config = yaml.safe_load(config_contents)

    # add hardcodes to config
    config['hardcode']['host'] = Hardcode.host
    config['hardcode']['port'] = Hardcode.port
    config['path']['state_cache'] = Hardcode.path_to_state_cache

    # add dotenv and return
    config['dotenv'] = read_dotenv(config, project_name)
    return config


def read_dotenv(config, project_name):
    # get path
    home = os.environ.get('HOME')
    path_to_dotenv = Path(home, '.env')

    # verify path
    if not os.path.exists(path_to_dotenv):
        print(f'path not exist : {path_to_dotenv}')
        exit()

    # open and read
    with open(path_to_dotenv, 'r') as dotenv_r:
        dotenv_lines = dotenv_r.readlines()

    # locate dotenv line
    project_dotenv = None
    for dotenv_line in dotenv_lines:
        if project_name in dotenv_line:
            project_dotenv = dotenv_line
            break

    # exit if not found
    if not project_dotenv:
        print(f'dotenv line not found, exit')
        exit()

    # build dotenv dict from line
    dotenv = {}
    dotenv_key_values = project_dotenv.split(';')[1:]
    for dotenv_key_value in dotenv_key_values:
        if '=' not in dotenv_key_value:
            continue
        key = dotenv_key_value.split('=')[0].strip()
        value = dotenv_key_value.split('=')[1].strip()
        dotenv[key] = value
    return dotenv
