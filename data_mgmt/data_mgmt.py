from qbit.q_enum import FilePriority


def sort_by_filename(file_list):
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
            'index': file.index,
            'priority': file.priority
        }

        # save file metadata by file name
        file_dict[file.name] = file_metadata

    # sort the dictionary keys by name
    file_dict_keys_sorted = sorted(file_dict)

    # using the sorted keys, rebuild the metadata dictionary in order
    #   of file.name. in addition, tally priority values as well as
    #   "sequential priority value streaks" for use in other functions

    # init objects needed for logic
    file_dict_sorted_by_name = {'file_names': {}}
    key_now = key_before = key_before_before = None
    group_of_three_found = False

    for idx, file_dict_key_sorted in enumerate(file_dict_keys_sorted):
        val_now = val_before = val_before_before = None

        # read values from the unsorted file_dict
        index = file_dict[file_dict_key_sorted]['index']
        priority = file_dict[file_dict_key_sorted]['priority']
        if group_of_three_found and priority == 0:
            file_dict_sorted_by_name['prioritized_file_keys'] = prioritized_file_keys

        there_are_two_previous_values = idx > 1
        if there_are_two_previous_values and \
                'prioritized_file_keys' not in file_dict_sorted_by_name:
            key_now = file_dict_key_sorted
            key_before = file_dict_keys_sorted[idx - 1]
            key_before_before = file_dict_keys_sorted[idx - 2]

            # get priority values of current and two previous keys
            val_now = priority
            val_before = \
                file_dict_sorted_by_name['file_names'][key_before]['priority']
            val_before_before = \
                file_dict_sorted_by_name['file_names'][key_before_before]['priority']

        group_of_three_found = False
        three_in_a_row_match = val_now and val_now == val_before == val_before_before
        if three_in_a_row_match:
            group_of_three_found = True
            prioritized_file_keys = [key_before_before, key_before, key_now]

        # write values to the newly name-sorted file_dict
        file_dict_sorted_by_name['file_names'][file_dict_key_sorted] = {
            'index': index,
            'priority': priority
        }

        # record the priority of the current run
    return file_dict_sorted_by_name
