# python lib imports
from json import dumps
from os.path import getmtime
# 3rd party imports
# project imports
from module.utils import _get_path_to


def write_search_memory(data: dict):
    path_to_search_memory = _get_path_to(['search', 'memory.json'])
    mtime_before = getmtime(path_to_search_memory)
    json_search_memory = dumps(data)
    with open(path_to_search_memory, 'w') as json_io:
        json_io.write(json_search_memory)
    _verify_write(mtime_before=mtime_before,
                  path_to_search_memory=path_to_search_memory)


def _verify_write(mtime_before, path_to_search_memory):
    mtime_after = getmtime(path_to_search_memory)
    mtime_changed = mtime_before != mtime_after
    if not mtime_changed:
        print(f"write failed")
        exit()
