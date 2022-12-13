# imports, python
from time import time
import os
import re

# imports, project
from qbit.q_enum import ENameType


def map_to_new_name_(old_name: str, guid_offset: int, name_maps: dict):
    # TODO next
    on_guid = get_guid_from_(old_name, guid_offset)

    if not on_guid:
        print(f'failed to create old_name guid from old_name : {old_name}')
        return

    # get appropriate name map
    if on_guid not in name_maps:
        print(f'no name_map for : {old_name} at {on_guid}')
        return

    # use name_maps to lookup how to build elements of the new name
    name_map = name_maps[on_guid]
    new_name = build_new_name_from_(name_map, on_guid, guid_offset)
    if not new_name:
        return None
    print(f'renamed TO : {new_name} FROM : {old_name}')
    return new_name

def get_guid_from_(old_name: str, guid_offset: int):
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

def build_new_name_from_(name_map, on_guid, guid_offset):
    old_name = get_e_name_from_guid(on_guid, guid_offset)
    name_type = name_map['type'] if 'type' in name_map else ENameType.none
    if name_type == ENameType.series:
        series_name = build_series_name_(old_name)
        if not series_name:
            return
        return series_name
    if name_type == ENameType.none:
        pass  # no plan for anything to happen here

def build_series_name_(old_name):
    rx_output = {}
    for rx_label, rx_filter in old_name['regex'].items():
        # apply each filter and validate output

        # prevent type mismatch
        rx_filter = str(rx_filter)

        rx_match = re.search(rx_filter, old_name)
        if not rx_match:
            rx_match = ''
        else:
            rx_match = rx_match[0]

        # pad single digits
        if rx_label == 'season':
            if len(rx_match) == 1:
                rx_match = '0' + rx_match

        # save output
        rx_output[rx_label] = rx_match
        pass

    # build name
    series_name = ''
    for label, value in rx_output.items():
        if value:
            if label == 'season':
                series_name = series_name + ', Season ' + value
                continue
            if series_name:
                series_name = series_name + ', ' + value
                continue
            series_name = series_name + value
    return series_name

def get_age_of_(path_to_item):
    item_stat = os.stat(path_to_item)
    item_accessed_sec = time() - item_stat.st_atime
    item_accessed_hour = item_accessed_sec / 3600
    return item_accessed_hour
