# imports, python
import os

# imports, third-party
import qbittorrentapi
import yaml

def add_name_maps_to_config(config: dict) -> dict:
    path_to_name_maps = config['path']['name_maps']
    if not os.path.exists(path_to_name_maps):
        print(f'path to name maps not exist : {path_to_name_maps}')
        exit()

    with open(path_to_name_maps, 'r') as nm_r:
        name_maps = yaml.safe_load(nm_r.read())

    if not name_maps:
        name_maps = {}

    assert isinstance(name_maps, dict), 'name_maps should be dict'
    config['name_maps'] = name_maps
    return config

def add_qbit_instance_to_config(config: dict) -> dict:
    qbit_instance = qbittorrentapi.Client(
        host=config['hardcode']['host'],
        port=config['hardcode']['port'],
        username=config['dotenv']['username'],
        password=config['dotenv']['password']
    )
    config['qbit_instance'] = qbit_instance
    return config
