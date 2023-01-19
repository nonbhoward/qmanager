# imports, python
from pathlib import Path
from time import gmtime
from time import sleep
from time import strftime
from time import time
import json
import os

# imports, project
from qbit.q_enum import EntryState
from qbit.q_enum import FilePriority
from qbit.q_enum import HistoricalKeys
from qmanager.cache import CacheController

# module globals
debug = False
timeout_debug = 600


class Qmanager:
    def __init__(self, config: dict):
        self.qbit = config['qbit_instance']
        self.path_to_cache = config['path']['cache']

        # init attributes assigned outside init
        self.cc = None

    def run(self):
        # load data
        self.read_cached_snapshots()
        self.read_snapshot_from_qbit()

        # task disk action
        self.manipulate_qbit_data_on_disk()

        # qbit client manipulation
        self.manipulate_qbit_metadata_via_qbit()

        # save/update data
        self.write_updated_snapshot_to_cache()

    def read_cached_snapshots(self):
        # FYI only two snapshots are kept so cache doesn't grow

        # verify
        if not os.path.exists(self.path_to_cache):
            create_new_cache(self.path_to_cache)

        # read cache
        with open(self.path_to_cache, 'r') as cache_r:
            json_cache = json.loads(cache_r.read())

        # save to class
        self.cc = CacheController(json_cache)

    def read_snapshot_from_qbit(self):
        # TODO could __dict__ make any objects better by attaching them
        #   to that object's __dict__? which objects?

        # TODO partition into two functions
        #   1. populates cache['client_data_snapshots'], done
        self.populate_client_data_snapshot()
        #   2. updates cache['entry_history_memory'], in-progress
        self.update_entry_history_memory()

    def populate_client_data_snapshot(self):
        # generate a new timestamped data collection
        ts_guid = get_timestamp()
        client_data = {ts_guid: {}}
        # convenience
        client_data_at_ts = client_data[ts_guid]

        # extract entry information from client
        all_entries = self.qbit.torrents.info()
        for entry in all_entries:
            e_hash = entry.hash
            e_data = {e_hash: {}}
            e_priorities = []
            # convenience
            e_data_at_hash = e_data[e_hash]

            for efd_file in entry.files.data:
                # build e_priorities for delta checking
                e_priorities.append(efd_file['priority'])

                # add efd data to entry data at this e_hash
                add_efd_files_data_to_(e_data_at_hash, efd_file)

            # save priorities and..?
            e_data_at_hash['e_priorities'] = e_priorities
            e_data_at_hash['all_delete'] = not any(e_priorities)

            # directly extract remaining dict key, vals
            for key, val in entry.items():
                e_data_at_hash.update({key: val})
            client_data_at_ts[e_hash] = e_data_at_hash

        # update the timestamp guid with the latest client data
        self.cc.cache['client_data_snapshots'].update({
            ts_guid: client_data_at_ts
        })

    def update_entry_history_memory(self):
        # init cache key if doesn't exist
        if 'entry_history_memory' not in self.cc.cache:
            self.cc.cache['entry_history_memory'] = {}

        # find latest data from client data snapshots
        cds = self.cc.cache['client_data_snapshots']
        cds_now = cds[sorted(cds)[-1]]
        # use it to update entry_history_memory
        ehm = self.cc.cache['entry_history_memory']

        # generate a timestamp for historical entry record data
        timestamp = get_timestamp()
        # extract whatever is relevant to history
        # & define which variables should be historic
        for e_hash, e_details in cds_now.items():
            if e_hash not in ehm:
                ehm[e_hash] = {}
            for e_detail_key, e_detail_value in e_details.items():
                if e_detail_key in HistoricalKeys.keys:
                    # create in advance for new entries
                    new_historical_dict = {
                        'is_historical': True,
                        'values': {timestamp: e_detail_value}}

                    if e_detail_key not in ehm[e_hash]:
                        ehm[e_hash][e_detail_key] = new_historical_dict
                        continue  # new historical var list initialized
                    if 'values' not in ehm[e_hash][e_detail_key]:
                        # a non-historical value was made historical
                        #   and this is the first run after that
                        ehm[e_hash][e_detail_key] = new_historical_dict
                        continue
                    ehm[e_hash][e_detail_key]['values'].update({
                        timestamp: e_detail_value
                    })
                    continue  # existing historical var list updated
                if e_detail_key not in ehm[e_hash]:
                    ehm[e_hash][e_detail_key] = e_detail_value

    def manipulate_qbit_data_on_disk(self):
        """A function to (ideally) locate all functions that manipulate
          data also managed by the qbit client
        """
        self.get_files_to_delete()
        self.delete_files()

        self.remove_empty_directories()
        self.remove_parts_files()
        self.recheck_error_entries()

        # resume anything that was left pausedDL and not otherwise started
        self.resume_paused()

    def get_files_to_delete(self):
        # convenience
        cds = self.cc.cache['client_data_snapshots']

        # abort if not two snapshots to compare
        enough_snapshots = len(cds) > 1
        if not enough_snapshots:
            return

        # sort snapshot keys to get two most recent
        ts_guids_sorted = sorted(cds.keys())
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

            # gather efd indices of files to delete
            delete_indices = []
            e_files_data = cds_after[e_hash]['efd_files_data']
            for idx, prio in enumerate(priorities_after):
                if prio == FilePriority.not_download:
                    delete_indices.append(idx)

            # use efd  indices to get entire efd file record
            files_to_delete = []
            for delete_index in delete_indices:
                files_to_delete.append(e_files_data[delete_index])

            # save to client data snapshot
            cds_after[e_hash]['files_to_delete'] = files_to_delete

    def delete_files(self):
        # FIXME delete_files overlooks files deselected if the entry has
        #   status completed
        # convenience
        cds = self.cc.cache['client_data_snapshots']

        # work with most recent
        ts_guid_after = sorted(cds.keys())[-1]
        cds_after = cds[ts_guid_after]

        # loop and delete
        for e_hash, e_details in cds_after.items():
            if 'files_to_delete' not in e_details:
                continue
            files_to_delete = e_details['files_to_delete']
            if not files_to_delete:
                continue
            e_state = e_details['state']
            if EntryState.error in e_state:
                e_name = e_details['name']
                print(f'error state at entry : {e_name}')
                self.recheck_and_resume(e_hash)
                continue
            for file_to_delete in files_to_delete:
                self.delete_file(e_hash, file_to_delete)
            self.recheck_and_resume(e_hash)

    def delete_file(self, e_hash, file_data, timeout_sec=15):
        timeout_sec = timeout_debug if debug else timeout_sec
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
            print(f'pausing {e_hash} to delete {f_name}')
            while not paused and not timeout:
                timeout = time() - start_time > timeout_sec
                if timeout:
                    print(f'pause timed out')
                    exit()
                e_state = self.qbit.torrents_info(
                    torrent_hashes=e_hash).data[0].state
                paused = True if EntryState.stopped in e_state else False
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
        # print(f'check if exist : {path_to_file}')
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

    def recheck_error_entries(self):
        print(f'checking for error status')
        # convenience
        cds = self.cc.cache['client_data_snapshots']

        ts_guids_sorted = sorted(cds)
        cds_now = cds[ts_guids_sorted[-1]]

        for e_hash, e_details in cds_now.items():
            e_state = e_details['state']
            if EntryState.error in e_state:
                self.qbit.torrents_recheck(torrent_hashes=e_hash)
            # TODO
            pass

    def recheck_and_resume(self, e_hash, timeout_sec=15):
        timeout_sec = timeout_debug if debug else timeout_sec
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

    def manipulate_qbit_metadata_via_qbit(self):
        pass

    def write_updated_snapshot_to_cache(self):
        # init core objects
        cache = self.cc.cache
        path_to_cache = self.path_to_cache

        # write to disk
        with open(path_to_cache, 'w') as cache_w:
            json.dump(cache, cache_w)

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

    def resume_paused(self):
        all_entries = self.qbit.torrents_info()
        for entry in all_entries:
            e_state = entry.state
            if EntryState.paused_dn in e_state:
                print(f'resume : {entry.name}')
                self.qbit.torrents_resume(entry.hash)


def create_new_cache(path_to_cache):
    print(f'file not exist : {path_to_cache}')
    try:
        print(f'attempt create file : {path_to_cache}')
        with open(path_to_cache, 'w') as new_cache:
            new_cache.write('{}')
    except Exception as exc:
        print(f'exception creating new cache : {exc}')
        raise exc


def get_timestamp():
    t_format = "%Y_%m%d_%H%M_%S"
    t_now = strftime(t_format, gmtime())
    return t_now

def add_efd_files_data_to_(e_data_at_hash, efd_file):
    """Extract k:v from efd_file and assign them to e_data_at_hash
    :param e_data_at_hash:
    :param efd_file:
    :return:
    """
    # convenience
    if 'files_to_delete' not in e_data_at_hash:
        # init ftd here so it's at top of debugger later..
        e_data_at_hash['files_to_delete'] = None

    # init efd metadata container (rooted on the efd index)..
    if 'efd_files_data' not in e_data_at_hash:
        e_data_at_hash['efd_files_data'] = {}

    # ..or update if already exists
    e_data_at_hash['efd_files_data'].update({
        efd_file['index']: {
            'availability': efd_file['availability'],
            'id': efd_file['id'],
            'name': efd_file['name'],
            'piece_range': efd_file['piece_range'],
            'priority': efd_file['priority'],
            'progress': efd_file['progress'],
            'size': efd_file['size'],
        }
    })
