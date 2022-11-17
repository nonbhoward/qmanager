# imports, python
import json
import os

# imports, project
from data_mgmt.data_mgmt import sort_by_filename
from qmanager.cache import StateHandler


class Qmanager:
    def __init__(self, config):
        self.qbit_instance = config['qbit_instance']
        self.path_to_cache = config['path']['cache']

        # init attributes assigned outside init
        self.cache = None

    def run(self):
        # read state cache
        self.read_state_cache()

        # get qbit state
        self.read_qbit_state()

        # increment triple-checkmark entries
        self.increment_sequential_triple_checkboxes()

        # write state cache
        self.write_state_cache()

    def read_state_cache(self):
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

        # if None, init as dict and create state_cache key
        if not json_cache:
            json_cache = {
                'state_cache': {}
            }

        # save to class
        self.cache = json_cache

    def read_qbit_state(self):
        # init core objects
        qbit = self.qbit_instance
        state_handler = StateHandler(self.cache)

        # extract entry information from client
        all_entries = qbit.torrents.info()
        for entry in all_entries:
            state_handler.set_files(entry.hash, entry.files.data)

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
        for e_hash, details in self.cache['state_cache'].items():
            file_list = details['files']
            entry_files_sorted_by_name = sort_by_filename(file_list)
            pass

    def write_state_cache(self):
        # init core objects
        path_to_state_cache = self.path_to_cache

        # write to disk
        with open(path_to_state_cache, 'w') as cache_w:
            json.dump(self.cache, cache_w)
