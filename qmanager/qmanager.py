# imports, python
import json
import os

# imports, project
from data_mgmt.data_mgmt import sort_by_filename
from qmanager.cache import CacheController


class Qmanager:
    def __init__(self, config: dict):
        self.qbit_instance = config['qbit_instance']
        self.path_to_cache = config['path']['cache']

        # init attributes assigned outside init
        self.cache = None
        self.cache_controller = None

    def run(self):
        # read state cache
        self.read_cache()

        # get qbit state
        self.read_qbit_state()

        # increment triple-checkmark entries
        self.increment_sequential_triple_checkboxes()

        # write state cache
        self.write_cache()

    def read_cache(self):
        # init core objects
        path_to_cache = self.path_to_cache

        # verify
        if not os.path.exists(path_to_cache):
            print(f'file not exist : {path_to_cache}')
            try:
                print(f'attempt create file : {path_to_cache}')
                with open(path_to_cache, 'w') as new_cache:
                    new_cache.write('{}')
            except Exception as exc:
                print(f'exception creating new cache : {exc}')
                raise exc

        # read cache
        with open(path_to_cache, 'r') as cache_r:
            cache_r_contents = cache_r.read()
            json_cache = json.loads(cache_r_contents)

        # if None, init as dict and create entry_cache key
        if not json_cache:
            json_cache = {
                'entry_cache': {}
            }

        # save to class
        self.cache = json_cache
        self.cache_controller = CacheController(self.cache)

    def read_qbit_state(self):
        # init core objects
        qbit = self.qbit_instance

        # extract entry information from client
        all_entries = qbit.torrents.info()
        for entry in all_entries:
            files = entry.files.data
            self.cache_controller.set_entry_files(entry.hash, files)

    def increment_sequential_triple_checkboxes(self):
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
        self.cache_controller.init_action_cache()
        for e_hash, details in self.cache_controller.get_entry_cache().items():
            file_list = details['files']
            file_list_w_grouped_keys = sort_by_filename(file_list)
            action_cache = {e_hash: file_list_w_grouped_keys}
            self.cache_controller.update_action_cache(action_cache)

        # next goal
        pass

    def write_cache(self):
        # init core objects
        path_to_cache = self.path_to_cache

        # write to disk
        with open(path_to_cache, 'w') as cache_w:
            json.dump(self.cache, cache_w)
