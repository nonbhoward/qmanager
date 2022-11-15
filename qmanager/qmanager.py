# imports, python
import json
import os


class Qmanager:
    def __init__(self, config):
        self.qbit_instance = config['qbit_instance']
        self.path_to_state_cache = config['path']['state_cache']

        # init attributes assigned outside init
        self.state_cache = None

    def run(self):
        pass
        # init core objects
        qbit = self.qbit_instance

        # read state cache
        self.read_state_cache()
        pass

        # get qbit state

        # increment triple-checkmark entries

        # write state cache
        self.write_state_cache()

    def read_state_cache(self):
        # init core objects
        path_to_state_cache = self.path_to_state_cache

        # verify
        if not os.path.exists(path_to_state_cache):
            print(f'file not exist : {path_to_state_cache}')
            exit()

        # read cache
        with open(path_to_state_cache, 'r') as state_cache_r:
            state_cache_r_contents = state_cache_r.read()
            json_state_cache = json.loads(state_cache_r_contents)

        # verify
        assert isinstance(json_state_cache, dict), 'state cache bad type'

        # save to class
        self.state_cache = json_state_cache

    def write_state_cache(self):
        # init core objects
        state_cache = self.state_cache
        path_to_state_cache = self.path_to_state_cache

        # write to disk
        with open(path_to_state_cache, 'w') as state_cache_w:
            json.dump(state_cache, state_cache_w)
