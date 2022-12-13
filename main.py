# imports, project
from qbit.q_enum import RunFrequency
from qmanager.qmanager import Qmanager
from config.read_local import read_config

qmanager = Qmanager(config=read_config())
qmanager.run(run_frequency=RunFrequency.per_fifth_minute)
