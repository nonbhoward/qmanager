# imports, third-party
import qbittorrentapi


def add_qbit_instance_to_config(config: dict) -> dict:
    qbit_instance = qbittorrentapi.Client(
        host=config['hardcode']['host'],
        port=config['hardcode']['port'],
        username=config['dotenv']['username'],
        password=config['dotenv']['password']
    )
    config['qbit_instance'] = qbit_instance
    return config
