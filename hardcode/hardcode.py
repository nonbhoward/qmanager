# imports, python
import os
from pathlib import Path

home = os.environ.get('HOME')
project_name = 'qmanager'


class Hardcode:
    # constants
    host = 'localhost'
    port = '8080'

    # building blocks
    project_name = project_name
    path_to_project = Path(home, 'git', project_name)

    # build
    path_to_cache = Path(path_to_project, 'cache', 'cache.json')
    path_to_config = Path(path_to_project, 'config', 'config.yaml')
