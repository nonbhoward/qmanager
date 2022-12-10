# imports, python
from pathlib import Path
from time import gmtime
from time import sleep
from time import strftime
from time import time
import json
import os

# imports, project
from data_mgmt.data_mgmt import get_deprioritized_files
from qbit.q_enum import EntryState
from qbit.q_enum import FilePriority
from qmanager.cache import CacheController


class Qmanager:
    def __init__(self, config: dict):
        self.qbit = config['qbit_instance']
        self.path_to_cache = config['path']['cache']

        # init attributes assigned outside init
        self.cc = None

    def run(self):
        self.read_cached_snapshots()
        self.build_snapshot_from_client_state()
        self.get_files_to_delete()
        self.delete_files()
        self.remove_empty_directories()
        self.recheck_error_entries()
        self.write_cache()
        self.remove_parts_files()
        self.resume_paused()

    def read_cached_snapshots(self):
        # verify
        if not os.path.exists(self.path_to_cache):
            print(f'file not exist : {self.path_to_cache}')
            try:
                print(f'attempt create file : {self.path_to_cache}')
                with open(self.path_to_cache, 'w') as new_cache:
                    new_cache.write('{}')
            except Exception as exc:
                print(f'exception creating new cache : {exc}')
                raise exc

        # read cache
        with open(self.path_to_cache, 'r') as cache_r:
            json_cache = json.loads(cache_r.read())

        # save to class
        self.cc = CacheController(json_cache)

    def build_snapshot_from_client_state(self):
        # generate a new timestamped data collection
        ts_guid = get_timestamp()
        client_data = {ts_guid: {}}

        # convenience
        client_data_at_ts = client_data[ts_guid]

        # extract entry information from client
        # comb the data, go ahead and comb it..
        all_entries = self.qbit.torrents.info()
        for entry in all_entries:
            e_hash = entry.hash
            e_data = {e_hash: {}}

            # convenience
            e_data_at_hash = e_data[e_hash]

            # extract metadata and build e_priorities which will be used
            #   to decide which entries to explore later, if the priorities
            #   have not changed, maybe do nothing?
            e_priorities = []
            for efd_file in entry.files.data:

                # convenience
                efd_index = efd_file['index']
                if 'files_to_delete' not in e_data_at_hash:
                    # init ftd here so it's at top of debugger later..
                    e_data_at_hash['files_to_delete'] = None
                if 'efd_files_data' not in e_data_at_hash:
                    e_data_at_hash['efd_files_data'] = {
                        efd_index: {}
                    }

                # convenience
                efd_file_priority = efd_file['priority']
                entry_file_data = {
                    'availability': efd_file['availability'],
                    'id': efd_file['id'],
                    'name': efd_file['name'],
                    'piece_range': efd_file['piece_range'],
                    'priority': efd_file_priority,
                    'progress': efd_file['progress'],
                    'size': efd_file['size'],
                }

                e_priorities.append(efd_file_priority)
                e_data_at_hash['efd_files_data'][efd_index] = entry_file_data

            # save priorities and..?
            e_data_at_hash['e_priorities'] = e_priorities
            e_data_at_hash['all_delete'] = not any(e_priorities)

            # directly extract dict vals
            for key, val in entry.items():
                e_data_at_hash.update({key: val})
            client_data_at_ts[e_hash] = e_data_at_hash
        self.cc.cache['client_data_snapshots'].update({
            ts_guid: client_data_at_ts
        })

    def get_files_to_delete(self):
        # convenience
        client_data_snapshots = self.cc.cache['client_data_snapshots']
        cds = client_data_snapshots

        # abort if not two snapshots to compare
        enough_snapshots = len(cds) > 1
        if not enough_snapshots:
            return

        # sort snapshot keys to get two most recent
        ts_guids_sorted = sorted(client_data_snapshots.keys())
        cds_after = cds[ts_guids_sorted[-1]]
        cds_before = cds[ts_guids_sorted[-2]]

        # delete all snapshot keys but two most recent
        for ts_guid_sorted in ts_guids_sorted[:-2]:
            del cds[ts_guid_sorted]

        # get files to be deleted
        # check if priorities have changed in two most recent ts_guids
        for e_hash, e_details in cds_after.items():
            priorities_after = cds_after[e_hash]['e_priorities']
            priorities_before = cds_before[e_hash]['e_priorities']
            priorities_changed = priorities_after != priorities_before
            if not priorities_changed:
                continue

            delete_indices = []
            e_files_data = cds_after[e_hash]['efd_files_data']
            for idx, prio in enumerate(priorities_after):
                if prio == FilePriority.not_download:
                    delete_indices.append(idx)
            files_to_delete = []
            for delete_index in delete_indices:
                files_to_delete.append(e_files_data[delete_index])
            cds_after[e_hash]['files_to_delete'] = files_to_delete

    def delete_files(self):
        # convenience
        cds = self.cc.cache['client_data_snapshots']

        # work with most recent
        ts_guid_after = sorted(cds.keys())[-1]
        cds_after = cds[ts_guid_after]

        # loop and delete shit
        for e_hash, e_details in cds_after.items():
            if 'files_to_delete' not in e_details:
                continue
            files_to_delete = e_details['files_to_delete']
            if not files_to_delete:
                continue
            for file_to_delete in files_to_delete:
                self.delete_file(e_hash, file_to_delete)
            self.recheck_and_resume(e_hash)

    def recheck_error_entries(self):
        print(f'checking for error status')
        # convenience
        client_data_snapshots = self.cc.cache['client_data_snapshots']
        cds = client_data_snapshots

        ts_guids_sorted = sorted(cds)
        cds_now = cds[ts_guids_sorted[-1]]

        for e_hash, e_details in cds_now.items():
            efd_state = e_details['state']
            efd_hash = e_details['hash']
            if EntryState.error in efd_state:
                self.qbit.torrents_recheck(torrent_hashes=efd_hash)

    def delete_file(self, e_hash, file_data, timeout_sec=15):
        e_info = self.qbit.torrents_info(torrent_hashes=e_hash)
        f_name = file_data['name']
        content_path = e_info.data[0].content_path

        # pause entry
        e_state = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].state
        paused = EntryState.paused_dn in e_state
        completed = EntryState.paused_up in e_state
        if not paused and not completed:
            self.qbit.torrents_pause(torrent_hashes=e_hash)

            # wait, verify paused
            paused, timeout, start_time = False, False, time()
            print(f'pausing {e_hash} to deselect {f_name}')
            while not paused and not timeout:
                timeout = time() - start_time > timeout_sec
                if timeout:
                    print(f'pause timed out')
                    exit()
                e_state = self.qbit.torrents_info(
                    torrent_hashes=e_hash).data[0].state
                paused = True if EntryState.paused_dn in e_state else False
                sleep(.25)
            print(f'pause successful')

        # find file on disk
        file_found = False
        path_to_file = None
        for root, _, files in os.walk(content_path):
            if file_found:
                break
            for file in files:
                if file in f_name:
                    path_to_file = Path(root, file)
                    file_found = True

        if not file_found:
            return

        # delete file from disk
        print(f'check if exist : {path_to_file}')
        if os.path.exists(path_to_file):
            try:
                print(f'delete from disk : {path_to_file}')
                os.remove(path_to_file)
            except Exception as exc:
                print(f'failed to delete file : {exc}')

    def remove_empty_directories(self):
        all_entries = self.qbit.torrents_info()
        content_paths = []
        for entry in all_entries:
            content_paths.append(entry.content_path)

        for content_path in content_paths:
            # delete empty child directories
            for e_root, e_dirs, _ in os.walk(content_path):
                if not e_dirs:
                    continue
                for e_dir in e_dirs:
                    e_dir_path = Path(e_root, e_dir)
                    content = os.listdir(e_dir_path)
                    if not content:
                        os.rmdir(e_dir_path)
                        print(f'removed : {e_dir_path}')

            # delete empty parent directories
            if not os.path.exists(content_path):
                continue
            if not os.path.isdir(content_path):
                continue
            content = os.listdir(content_path)
            if not content:
                os.rmdir(content_path)
                print(f'removed : {content_path}')

    def recheck_and_resume(self, e_hash, timeout_sec=15):
        e_name = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].name

        # force recheck
        print(f'rechecking {e_name}')
        self.qbit.torrents_recheck(torrent_hashes=e_hash)

        # wait for recheck to complete
        checking = True
        timeout, start_time = False, time()
        while checking and not timeout:
            timeout = time() - start_time > timeout_sec
            if timeout:
                print(f'checking timed out')
                exit()
            checking = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].state_enum.is_checking

        # resume
        self.qbit.torrents_resume(torrent_hashes=e_hash)

    def remove_parts_files(self):
        path_to_parts = self.qbit.app.default_save_path
        items = os.listdir(path_to_parts)
        for item in items:
            starts_with_period = item.startswith('.')
            ends_with_parts = item.endswith('.parts')
            if starts_with_period and ends_with_parts:
                path_to_part_file = Path(path_to_parts, item)
                print(f'remove parts file : {path_to_part_file}')
                os.remove(path_to_part_file)

    def write_cache(self):
        # init core objects
        cache = self.cc.cache
        path_to_cache = self.path_to_cache

        # write to disk
        with open(path_to_cache, 'w') as cache_w:
            json.dump(cache, cache_w)

    def resume_paused(self):
        all_entries = self.qbit.torrents_info()
        for entry in all_entries:
            e_state = entry.state
            if EntryState.paused_dn in e_state:
                print(f'resume : {entry.name}')
                self.qbit.torrents_resume(entry.hash)


def get_timestamp():
    t_format = "%Y_%m%d_%H%M"
    t_now = strftime(t_format, gmtime())
    return t_now
