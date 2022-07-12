# python lib imports
# 3rd party imports
# project imports
from module.config_reader import read_configuration
from module.qmanager import QManager
from module.search_memory_reader import read_search_memory

# read app config and search memory
app_config = read_configuration()
search_memory = read_search_memory()

# instantiate objects
qmanager = QManager(app_config=app_config,
                    search_memory=search_memory,
                    loops_per_run=3)

# run program
qmanager.run()
