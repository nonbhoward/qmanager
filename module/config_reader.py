# python lib imports
# 3rd party imports
# project imports
from module.utils import _get_path_to
import yaml


def read_configuration():
    path_to_config = _get_path_to(['config', 'config.yaml'])
    with open(path_to_config, 'r') as raw_config:
        config = yaml.safe_load(raw_config)
    if not isinstance(config, dict):
        print(f"config is not of type dict")
        exit()
    return config
