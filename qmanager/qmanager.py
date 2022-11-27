# imports, python
from pathlib import Path
from time import sleep
from time import time
import json
import os

# imports, project
from data_mgmt.data_mgmt import get_files_to_delete
from qbit.q_enum import EntryState
from qbit.q_enum import FilePriority
from qmanager.cache import CacheController


class Qmanager:
    def __init__(self, config: dict):
        self.qbit_instance = config['qbit_instance']
        self.path_to_cache = config['path']['cache']

        # init attributes assigned outside init
        self.cache = None
        self.cache_controller = None

    def run(self):
        # get qbit state
        self.build_entry_cache()

        # correct any entries in error state
        self.recheck_error_entries()

        # read entry cache > populate action cache
        self.parse_actions_from_entry_cache()

        # execute action cache
        self.execute_action_cache()

    def read_cache(self):
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

        # if None, init as dict and create entry_cache key
        if not json_cache:
            json_cache = {
                'entry_cache': {}
            }

        # save to class
        self.cache = json_cache
        self.cache_controller = CacheController(self.cache)

    def build_entry_cache(self):
        # init core objects
        qbit = self.qbit_instance

        # extract entry information from client
        all_entries = qbit.torrents.info()
        for entry in all_entries:
            files = entry.files.data
            self.cache_controller.set_entry_files(entry.hash, files)

    def recheck_error_entries(self):
        qbit = self.qbit_instance
        all_entries = qbit.torrents.info()
        for entry in all_entries:
            if entry.state_enum.is_errored:
                qbit.torrents_recheck(torrent_hashes=entry.hash)

    def parse_actions_from_entry_cache(self):
        self.cache_controller.init_action_cache()
        action_cache = {}
        # read entry hash, looking for sequentially selected filenames
        # this target represents three prioritized files in a row
        # TODO abstract this more clearly
        target = [0, 1, 1, 1, 0]
        for e_hash, details in self.cache_controller.get_entry_cache().items():
            file_list = details['files']
            files_to_delete = {
                'file_delete_metadata': get_files_to_delete(file_list, target)
            }
            action_cache[e_hash] = files_to_delete
        self.cache_controller.update_action_cache(action_cache)

    def execute_action_cache(self):
        action_cache = self.cache['action_cache']
        for e_hash, details in action_cache.items():
            if not details['file_delete_metadata']['files_to_delete']:
                continue
            ftm = details['file_delete_metadata']
            for ftd_key in ftm['files_to_delete']:
                e_id = details['file_delete_metadata']['file_names'][
                    ftd_key]['entry_id']
                self.delete_file(e_hash=e_hash, e_id=e_id)
                e_id = None
            self.recheck_and_resume(e_hash)

    def delete_file(self, e_hash, e_id, timeout_sec=15):
        qbit = self.qbit_instance
        e_info = qbit.torrents_info(torrent_hashes=e_hash)
        f_name = e_info.data[0].files.data[e_id].name
        content_path = e_info.data[0].content_path

        # pause entry
        qbit.torrents_pause(torrent_hashes=e_hash)

        # wait, verify paused
        paused, timeout, start_time = False, False, time()
        print(f'pausing {e_hash} to deselect {f_name}')
        while not paused and not timeout:
            timeout = time() - start_time > timeout_sec
            if timeout:
                print(f'pause timed out')
                exit()
            e_state = qbit.torrents_info(
                torrent_hashes=e_hash).data[0].state
            paused = True if EntryState.paused in e_state else False
            sleep(.25)
        print(f'pause successful')

        # unselect
        print(f'deselecting {f_name}')
        qbit.torrents_file_priority(torrent_hash=e_hash,
                                    file_ids=e_id,
                                    priority=FilePriority.not_download)

        # wait, verify unselected
        selected, timeout, start_time = True, False, time()
        while selected and not timeout:
            timeout = time() - start_time > timeout_sec
            if timeout:
                print(f'deselect timed out')
                exit()
            f_priority = qbit.torrents_info(
                torrent_hashes=e_hash).data[0].files.data[e_id].priority
            selected = f_priority == 1
        print(f'deselect successful')

        # find file on disk
        file_found = False
        path_to_file = None
        for root, _, files in os.walk(content_path):
            for file in files:
                file_found = file in f_name
                if file_found:
                    path_to_file = Path(root, file)
                    break

        if not file_found:
            print(f'file not found : {f_name}')
            return

        # delete file from disk
        print(f'check if exist : {path_to_file}')
        if os.path.exists(path_to_file):
            try:
                print(f'delete from disk : {path_to_file}')
                os.remove(path_to_file)
            except Exception as exc:
                print(f'failed to delete file : {exc}')

    def recheck_and_resume(self, e_hash, timeout_sec=15):
        qbit = self.qbit_instance
        e_name = qbit.torrents_info(torrent_hashes=e_hash).data[0].name

        # force recheck
        print(f'rechecking {e_name}')
        qbit.torrents_recheck(torrent_hashes=e_hash)

        # wait for recheck to complete
        checking = True
        timeout, start_time = False, time()
        while checking and not timeout:
            timeout = time() - start_time > timeout_sec
            if timeout:
                print(f'checking timed out')
                exit()
            # TODO not sure if this works
            checking = qbit.torrents_info(torrent_hashes=e_hash).data[0].state_enum.is_checking

        # resume
        qbit.torrents_resume(torrent_hashes=e_hash)

    def write_cache(self):
        # init core objects
        path_to_cache = self.path_to_cache

        # write to disk
        with open(path_to_cache, 'w') as cache_w:
            json.dump(self.cache, cache_w)
