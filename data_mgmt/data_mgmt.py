from qbit.q_enum import FilePriority


def get_deprioritized_files(file_list):
    """Delete all files with do not download priority

    :param file_list: all files associated with an entry
    :return:
    """
    file_delete_metadata = {'file_names': {}}
    for file in file_list:
        e_id = file.id
        e_priority = file.priority
        if e_priority == FilePriority.not_download:
            file_delete_metadata['file_names'][file.name] = {
                'entry_id': e_id,
                'name': file.name
            }
    return file_delete_metadata
