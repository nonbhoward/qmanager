# imports, python
from time import time
import os
import re

# imports, project
from qbit.q_enum import ENameType


def map_to_new_name_(e_hash: str, name_maps: dict):
    # ensure the name_map exists at the hash
    if e_hash not in name_maps:
        print(f'hash not found : {e_hash}')
        return

    # ensure the name_map contains regex key
    name_map = name_maps[e_hash]
    key = 'regex'
    if key not in name_map:
        print(f'key not found at {e_hash} : {key}')
        return

    name_map_regex = name_map['regex']
    for name_map_key, name_map_value in name_map_regex.items():
        if name_map_value is None:
            print(f'missing regex val at {e_hash} for : {name_map_key}')
            return

    # use name_maps to lookup how to build elements of the new name
    old_name = name_map['oldest_name']
    new_name = build_new_name_from_(name_map)
    print(f'renamed TO : {new_name} FROM : {old_name}')
    return new_name


def get_guid_from_(old_name: str, guid_offset: int):
    # TODO delete if unused
    guid_name = ''
    for letter in old_name:
        letter_num = ord(letter)
        new_letter_num = letter_num + guid_offset
        new_letter = chr(new_letter_num)
        guid_name += new_letter
    return guid_name


def get_e_name_from_guid(on_guid: str, guid_offset: int):
    new_name = ''
    for letter in on_guid:
        letter_num = ord(letter)
        new_letter_num = letter_num - guid_offset
        new_letter = chr(new_letter_num)
        new_name += new_letter
    return new_name


def build_new_name_from_(name_map):
    series_name = build_series_name_(name_map)
    if not series_name:
        return
    return series_name


def build_series_name_(name_map):
    old_name = name_map['oldest_name']
    regex_output = {}
    for regex_label, regex_filter in name_map['regex'].items():
        # apply each filter and validate output

        # prevent type mismatch
        regex_filter = str(regex_filter)

        regex_match_found = re.search(regex_filter, old_name)
        if not regex_match_found:
            # TODO keep as var? how is it more useful?
            no_regex_match_found = 'no_regex_match_found'
            regex_match_found = no_regex_match_found
        else:
            regex_match_found = regex_match_found[0]

        # pad single digits
        if regex_label == 'season':
            only_one_character = len(regex_match_found) == 1
            if only_one_character:
                regex_match_found = '0' + regex_match_found

        # save output
        regex_output[regex_label] = regex_match_found
        pass

    # build name
    full_entry_name = ''
    for regex_label, regex_match_found in regex_output.items():
        if regex_match_found:
            if regex_label == 'season':
                full_entry_name = full_entry_name + ', Season ' + regex_match_found
                continue
            if full_entry_name:
                full_entry_name = full_entry_name + ', ' + regex_match_found
                continue
            full_entry_name = full_entry_name + regex_match_found
    return full_entry_name


def get_age_of_(path_to_item):
    item_stat = os.stat(path_to_item)
    item_accessed_sec = time() - item_stat.st_atime
    item_accessed_hour = item_accessed_sec / 3600
    return item_accessed_hour
