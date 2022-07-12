# python lib imports
from os import getcwd
from os.path import exists
from pathlib import Path
# 3rd party imports
# project imports


def _get_path_to(path_elements: list) -> Path:
    path_to_project = Path(getcwd())
    path_to_element = Path(path_to_project, * path_elements)
    if not exists(path_to_element):
        print(f"{path_to_element} does not exist")
        exit()
    return path_to_element
