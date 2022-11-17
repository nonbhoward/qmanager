class CacheController:
    def __init__(self, cache):
        self.cache = cache

    def get_entry_cache(self):
        return self.cache['entry_cache']

    def get_entry_files(self, entry_hash):
        return self.cache['entry_cache'][entry_hash]['files']

    def init_action_cache(self):
        self.cache['action_cache'] = {}

    def set_entry_files(self, entry_hash, files):
        if entry_hash not in self.cache['entry_cache']:
            self.cache['entry_cache'][entry_hash] = {'files': files}

    def update_action_cache(self, action_cache):
        self.cache['action_cache'].update(action_cache)
