def find_prioritized_file_keys(file_list):
    """
    :param file_list:
    :return:
    """
    # create a metadata dictionary keyed by filename in the same order as
    #   the entry.files.data list
    file_dict = {}
    for file in file_list:
        # extract file metadata
        file_metadata = {
            'id': file.id,
            'priority': file.priority
        }

        # save file metadata by file name
        file_dict[file.name] = file_metadata

    # sort the dictionary keys by name
    file_dict_keys_sorted = sorted(file_dict)

    # using the sorted keys, rebuild the metadata dictionary in order
    #   of file.name. in addition, look for grouped priority values and
    #   retrieve associated keys

    # init objects
    fns_and_pfk = {'file_names': {}}
    # init objects needed for priority hunting
    file_03_keep = file_02_keep = file_01_delete = None
    group_of_three_found = False
    prioritized_file_keys = {}
    get_next_value = False

    priorities = []
    for file_dict_key_sorted in file_dict_keys_sorted:
        # write values to the newly name-sorted file_dict
        entry_id = file_dict[file_dict_key_sorted]['id']
        entry_priority = file_dict[file_dict_key_sorted]['priority']
        fns_and_pfk = fns_and_pfk
        fns_and_pfk['file_names'][file_dict_key_sorted] = {
            'entry_id': entry_id,
            'entry_priority': entry_priority
        }
        priorities.append(entry_priority)

    priorities_count = len(priorities)
    action_indices = []
    for idx in range(priorities_count):
        sample = [priority for priority in priorities[idx:idx+5]]
        target = [0, 1, 1, 1, 0]
        if target == sample:
            action_indices = [idx + 1, idx + 2, idx + 3]
        action_keys = []
        for action_index in action_indices:
            action_keys.append(file_dict_keys_sorted[action_index])
        if action_keys:
            prioritized_file_keys = {
                'file_01_delete': action_keys[0]
            }
    fns_and_pfk['prioritized_file_keys'] = prioritized_file_keys
    return fns_and_pfk
