def extract_sequentially_prioritized_metadata(entry_files_sorted_by_name):
    """This function's role is to check priorities, identifying the pattern
      of three file.name sorted files each with a non-zero priority. When
      three files are selected, they represent the following :

      File #1 : file was watched <~ will be unselected and deleted
      File #2 : file being watched <~ no action
      File #3 : file to be watched <~ no action

    After file #1 is deleted, it is unselected, two files are left
      selected and this sequence detector will pass over it until a third
      file is selected at a later date.
    """
    pass


def sort_by_filename(file_list):
    # create a metadata dictionary keyed by filename in the same order as
    #   the entry.files.data list
    file_dict = {}
    for file in file_list:
        file_dict[file.name] = {
            'index': file.index,
            'priority': file.priority
        }

    # sort the dictionary keys by name
    file_dict_keys_sorted = sorted(file_dict)

    # using the sorted keys, rebuild the metadata dictionary in order
    #   of file.name
    file_dict_sorted_by_name = {}
    for file_dict_key_sorted in file_dict_keys_sorted:
        file_dict_sorted_by_name[file_dict_key_sorted] = {
            'index': file_dict[file_dict_key_sorted]['index'],
            'priority': file_dict[file_dict_key_sorted]['priority']
        }
    return file_dict_sorted_by_name
