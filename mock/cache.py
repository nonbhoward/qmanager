# imports, python
from time import gmtime
from time import strftime

ts_guid_01 = strftime("%Y_%m%d_%H%M", gmtime())

hash_01 = 'abc'
hash_02 = 'def'

cache = {
    'client_data': {
        ts_guid_01: {
            hash_01: {},
            hash_02: {}
        },
    }
}
