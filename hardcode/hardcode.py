# imports, python
import os
from pathlib import Path

home = os.environ.get('HOME')
project_name = 'qmanager'


class Hardcode:
    # paths
    project_name = project_name
    path_to_project = Path(home, 'git', project_name)
    path_to_state_cache = Path(path_to_project, 'cache', 'state.json')
    path_to_config = Path(path_to_project, 'config', 'config.yaml')

    # constant values
    host = 'localhost'
    port = '8080'
