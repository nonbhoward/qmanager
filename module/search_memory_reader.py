# python lib imports
# 3rd party imports
# project imports
from module.utils import _get_path_to


def read_search_memory():
    path_to_search_memory = _get_path_to(['search', 'memory.json'])
    with open(path_to_search_memory, 'r') as raw_memory:
        search_memory = raw_memory.read()
    return search_memory
