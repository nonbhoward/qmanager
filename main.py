# imports, project
from qbit.qbit import add_qbit_instance_to_config
from qmanager.qmanager import Qmanager
from read_local.read_local import read_config

config = read_config()
config = add_qbit_instance_to_config(config)
qmanager = Qmanager(config=config)
qmanager.run()
