def get_files_to_delete(file_list, target):
    """
    This function's role is to check priorities, identifying the pattern
      of x # of file.name sorted files each with a non-zero priority. When
      x files are selected, they represent the following :

      File n+0 : file was watched <~ will be unselected and deleted
      File n+1 : file being watched <~ no action
      File n+2 : file to be watched <~ no action

    After file #1 is deleted, it is unselected, two files are left
      selected and this sequence detector will pass over it until a target
      file is selected at a later date.

    :param file_list: list of files taken directly from client
    :param target: prioritized file pattern to seek
    :return: dictionaried data with files to delete
    """
    # convert file_list to dictionary keyed by file.name
    file_dict = {}
    for file in file_list:
        file_metadata = {
            'id': file.id,
            'priority': file.priority}
        file_dict[file.name] = file_metadata

    # sort the dictionary keys by name
    file_names_sorted = sorted(file_dict)

    # using the sorted keys, rebuild the metadata dictionary in order
    #   of file.name

    # init objects
    file_metadata_sorted = {'file_names': {}}
    e_priorities = []
    for idx, file_name in enumerate(file_names_sorted):
        # needed when actions are performed on specific files
        file_metadata_sorted['file_names'][file_name] = {
            'entry_id': file_dict[file_name]['id'],
        }
        # needed to detect pattern
        e_priorities.append(file_dict[file_name]['priority'])
        if idx == len(file_names_sorted) - 1:
            file_metadata_sorted['e_priorities'] = e_priorities

    # look for grouped priorities and retrieve associated keys
    files_to_delete = []
    for idx in range(len(e_priorities)):
        sample = [priority for priority in e_priorities[idx:idx+5]]
        # TODO add case to handle "first file"
        if target == sample:
            file_name_to_delete = file_names_sorted[idx + 1]
            files_to_delete.append(file_name_to_delete)
        if idx == len(e_priorities) - 1:
            file_metadata_sorted['files_to_delete'] = files_to_delete
    return file_metadata_sorted
