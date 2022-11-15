class StateHandler:
    def __init__(self, cache):
        self.cache = cache

    def get_files(self, entry_hash):
        return self.cache['state_cache'][entry_hash]['files']

    def set_files(self, entry_hash, files):
        if entry_hash not in self.cache['state_cache']:
            self.cache['state_cache'][entry_hash] = {}
        self.cache['state_cache'][entry_hash]['files'] = files
