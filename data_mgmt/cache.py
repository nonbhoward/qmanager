empty_cache = {
    'client_data_snapshots': {}
}


class CacheController:
    def __init__(self, cache):
        self.cache = cache
        if not self.cache:
            self.cache = empty_cache

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, value):
        self._cache = value
