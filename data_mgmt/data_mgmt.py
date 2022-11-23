def find_prioritized_file_keys(file_list):
    """
    TODO note that itertools.groupby could have been useful here

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
    file_names_sorted_and_prioritized_file_keys = {'file_names': {}}
    # init objects needed for priority hunting
    file_03_keep = file_02_keep = file_01_delete = None
    group_of_three_found = False
    prioritized_file_keys = {}
    get_next_value = False

    for idx, file_dict_key_sorted in enumerate(file_dict_keys_sorted):
        val_03 = val_02 = val_to_delete = None

        if get_next_value:
            file_04_select = file_dict_key_sorted
            prioritized_file_keys['file_04_select'] = file_04_select
            get_next_value = False

        # read values from the unsorted file_dict
        entry_priority = file_dict[file_dict_key_sorted]['priority']
        if group_of_three_found and entry_priority == 0:
            file_names_sorted_and_prioritized_file_keys['prioritized_file_keys'] = \
                prioritized_file_keys

        there_are_two_previous_values = idx > 1
        if there_are_two_previous_values and \
                'prioritized_file_keys' not in file_names_sorted_and_prioritized_file_keys:
            file_01_delete = file_dict_keys_sorted[idx - 2]
            file_02_keep = file_dict_keys_sorted[idx - 1]
            file_03_keep = file_dict_key_sorted

            # init shortcuts
            file_names = file_names_sorted_and_prioritized_file_keys['file_names']
            entry_before = file_names[file_02_keep]
            entry_before_before = file_names[file_01_delete]

            # get priority values of current and two previous keys
            val_03 = entry_priority
            val_02 = entry_before['entry_priority']
            val_to_delete = entry_before_before['entry_priority']

        group_of_three_found = False
        three_in_a_row_match = val_03 and val_03 == val_02 == val_to_delete
        if three_in_a_row_match:
            group_of_three_found = True
            prioritized_file_keys = {
                'file_01_delete': file_01_delete,
                'file_02_keep': file_02_keep,
                'file_03_keep': file_03_keep
            }
            get_next_value = True

        # write values to the newly name-sorted file_dict
        entry_id = file_dict[file_dict_key_sorted]['id']
        fns_and_pfk = file_names_sorted_and_prioritized_file_keys
        fns_and_pfk['file_names'][file_dict_key_sorted] = {
            'entry_id': entry_id,
            'entry_priority': entry_priority
        }

    return file_names_sorted_and_prioritized_file_keys
