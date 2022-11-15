# imports, python
import os
from pathlib import Path


class Hardcode:
    # get a root
    home = os.environ.get('HOME')
    if not home:  # nt compatibility
        home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']

    # constants
    project_name = 'qmanager'
    host = 'localhost'
    port = '8080'

    # building blocks
    project_name = project_name
    path_to_project = Path(home, 'git', project_name)

    # build
    path_to_cache = Path(path_to_project, 'cache', 'cache.json')
    path_to_config = Path(path_to_project, 'config', 'config.yaml')
