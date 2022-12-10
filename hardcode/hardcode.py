# imports, python
import os
from pathlib import Path

# dn=dir_name, fn=filename, ext=extension
cache_dn = 'cache'
cache_fn = 'cached_snapshots'
cache_ext = '.json'

config_dn = 'config'
config_fn = 'config'
config_ext = '.yaml'

projects_dn = 'git'


class Hardcode:
    # get a root
    home = os.environ.get('HOME')
    if not home:  # nt compatibility
        home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']

    # client constants
    project_name = 'qmanager'
    host = 'localhost'
    port = '8080'

    # building blocks
    project_name = project_name
    path_to_project = Path(home, projects_dn, project_name)

    # build
    path_to_cache = Path(path_to_project, cache_dn, cache_fn + cache_ext)
    path_to_config = Path(path_to_project, config_dn, config_fn + config_ext)
