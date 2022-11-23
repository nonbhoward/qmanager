def find_pfks(file_list, target):
    """
    pfk = prioritized file keys
    This function's role is to check priorities, identifying the pattern
      of x # of file.name sorted files each with a non-zero priority. When
      x files are selected, they represent the following :

      File n : file was watched <~ will be unselected and deleted
      File n+1 : file being watched <~ no action
      File n+2 : file to be watched <~ no action
      File n+..

    After file #1 is deleted, it is unselected, two files are left
      selected and this sequence detector will pass over it until a target
      file is selected at a later date.

    :param file_list: list of files taken directly from client
    :param target: prioritized file pattern to seek
    :return: dictionaried data with keys to identify prioritized files
    """
    # create a metadata dictionary keyed by filename in the same order as
    #   the entry.files.data list. used to generate alphabetical filenames
    #   as well as providing a way to extract metadata by filename
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
    file_names_sorted = sorted(file_dict)

    # using the sorted keys, rebuild the metadata dictionary in order
    #   of file.name

    # init objects
    # fns_and_pfk = "filenames and prioritized file keys"
    fns_and_pfk = {'file_names': {}}
    prioritized_file_keys = {}
    e_priorities = []
    for file_name in file_names_sorted:
        # write values to the newly name-sorted file_dict
        fns_and_pfk['file_names'][file_name] = {
            'entry_id': file_dict[file_name]['id'],
            'entry_priority': file_dict[file_name]['priority']
        }
        e_priorities.append(file_dict[file_name]['priority'])

    # look for grouped priority values and retrieve associated keys
    action_indices = []
    for idx in range(len(e_priorities)):
        sample = [priority for priority in e_priorities[idx:idx+5]]
        if target == sample:
            action_indices = [idx + 1, idx + 2, idx + 3]
        action_keys = []
        for action_index in action_indices:
            action_keys.append(file_names_sorted[action_index])
        if action_keys:
            prioritized_file_keys = {
                'file_01_delete': action_keys[0]
            }
    fns_and_pfk['prioritized_file_keys'] = prioritized_file_keys
    return fns_and_pfk
