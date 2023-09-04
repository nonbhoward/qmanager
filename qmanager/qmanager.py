# imports, python
import copy
from pathlib import Path
from time import gmtime, sleep, strftime, time
import json
import os

# imports, third-party
import psutil
import yaml

# imports, project
from data_mgmt.cache import CacheController
from data_mgmt.data_mgmt import get_age_of_
from data_mgmt.data_mgmt import get_guid_from_
from data_mgmt.data_mgmt import map_to_new_name_
from dev.flags import debug
from dev.flags import run_frequency_debug
from dev.flags import timeout_debug
from dev.wrapper import announce_duration
from qbit.q_enum import DataRate
from qbit.q_enum import Default
from qbit.q_enum import EStateEnum
from qbit.q_enum import FilePriority
from qbit.q_enum import HistoricalKeys
from qbit.q_enum import PartsAge
from qbit.q_enum import QbitProcess
from qbit.q_enum import UserPrompt
from qbit.qbit import add_qbit_instance_to_config
from qbit.qbit import add_name_maps_to_config

# user prompts
debug_warning = UserPrompt.debug_flag_warning if debug else ''


class Qmanager:
    def __init__(self, config: dict):
        self.config = config

        # init attributes assigned outside init
        self.qbit = None
        self.cc = None
        self.stats = {
            'rename': {}
        }

    # FUNCTION TIER 01, Top-level program flow
    # run(), main_loop()

    def run(self, run_frequency):
        while True:
            if qbit_is_running():
                try:
                    self.main_loop()
                except Exception as exc:
                    # TODO dump exc stack to log
                    print(f'crash : {exc}')
                    raise exc
            main_loop_wait(run_frequency)

    @announce_duration
    def main_loop(self):
        # get qbit instance
        self.config = add_qbit_instance_to_config(self.config)
        self.qbit = self.config['qbit_instance']
        # get rename details
        self.config = add_name_maps_to_config(self.config)

        # load data
        self.read_cached_snapshots()
        self.read_snapshot_from_qbit()

        # task disk action
        self.manipulate_qbit_data_on_disk()

        # qbit client manipulation
        self.manipulate_qbit_metadata_via_qbit()

        # save/update data
        self.write_updated_snapshot_to_cache()

    # FUNCTION TIER 02, Mid-level program flow
    # loading data : read_cached_snapshots(), read_snapshot_from_qbit()
    # disk actions : manipulate_qbit_data_on_disk()
    # qbit client actions : manipulate_qbit_metadata_via_qbit()
    # saving data : write_updated_snapshot_to_cache()
    # loop delay : main_loop_wait()

    @announce_duration
    def read_cached_snapshots(self):
        # FYI only two snapshots are kept so cache doesn't grow
        path_to_cache = self.config['path']['cache']

        # verify
        if not os.path.exists(path_to_cache):
            create_new_cache(path_to_cache)

        # read cache
        with open(path_to_cache, 'r') as cache_r:
            size_mb = str(os.stat(path_to_cache).st_size / 1000000)[:-4]
            print(f'cache size is {size_mb} megabytes')
            json_cache = json.loads(cache_r.read())

        # save to class
        self.cc = CacheController(json_cache)

    @announce_duration
    def read_snapshot_from_qbit(self):
        # TODO could __dict__ make any objects better by attaching them
        #   to that object's __dict__? which objects?
        self.populate_client_data_snapshot()
        self.update_entry_history_memory()  # Prevents cache growth

    @announce_duration
    def manipulate_qbit_data_on_disk(self):
        """A place to (ideally) locate all functions that manipulate
          data which is also managed by the qbit client
        """
        self.get_files_to_delete()
        self.delete_files()

        self.remove_empty_directories()
        self.remove_parts_files(old_age_threshold=PartsAge.one_week)

        self.init_new_hashes_in_name_maps()

    @announce_duration
    def manipulate_qbit_metadata_via_qbit(self, resurrect=False):
        # entry label rename
        self.apply_rename_map()
        # set categories
        self.categorize_uncategorized()
        # set download rates
        self.enforce_download_rates()
        # set upload rates
        self.enforce_upload_rates()
        # set share ratio
        self.enforce_share_ratios()
        # remove unused categories
        self.pause_completed()
        if resurrect:
            self.resurrect_entry_history_memory()
        self.recheck_error_entries()
        # resume anything that was left pausedDL and not otherwise started
        self.resume_paused()

    @announce_duration
    def write_updated_snapshot_to_cache(self):
        # init core objects
        cache = self.cc.cache
        path_to_cache = self.config['path']['cache']

        # write to disk
        with open(path_to_cache, 'w') as cache_w:
            json.dump(cache, cache_w)

    # FUNCTION TIER 03, Low-level program flow
    # loading data : create_new_cache(), populate_client_data_snapshot(),
    #   update_entry_history_memory()
    # disk actions : get_files_to_delete(), delete_files(),
    #   remove_empty_directories(), remove_parts_files(),
    # qbit client actions : apply_rename_map(), categorize_uncategorized(),
    #   enforce_download_rates(), enforce_upload_rates(),
    #   enforce_share_ratios(), pause_completed(),
    #   recheck_error_entries(), resume_paused(), reset_name_to_original(),
    #   resurrect_entry_history_memory()
    # saving data : NONE
    # loop delay : NONE

    def populate_client_data_snapshot(self):
        # generate a new timestamped data collection
        ts_guid = get_timestamp()
        client_data = {ts_guid: {}}
        # convenience
        client_data_at_ts = client_data[ts_guid]

        # extract entry information from client
        all_entries = self.qbit.torrents.info()
        for entry in all_entries:
            e_data = {entry.hash: {}}
            e_priorities = []

            for efd_file in entry.files.data:
                # build e_priorities for delta checking
                e_priorities.append(efd_file['priority'])

                # add efd data to entry data at this e_hash
                add_efd_files_data_to_(e_data[entry.hash], efd_file)

            # save priorities and..?
            e_data[entry.hash]['e_priorities'] = e_priorities
            e_data[entry.hash]['all_delete'] = not any(e_priorities)

            # directly extract remaining dict key, vals
            for key, val in entry.items():
                e_data[entry.hash].update({key: val})
            client_data_at_ts[entry.hash] = e_data[entry.hash]

        # update the timestamp guid with the latest client data
        self.cc.cache['client_data_snapshots'].update({
            ts_guid: client_data_at_ts
        })

    def update_entry_history_memory(self):
        # init cache key if doesn't exist
        if 'entry_history_memory' not in self.cc.cache:
            self.cc.cache['entry_history_memory'] = {}

        # find latest data from client data snapshots
        cds_now = self.get_latest_snapshot()
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
                if e_detail_key in HistoricalKeys.active:
                    # create in advance for new entries
                    new_historical_dict = {
                        'is_historical': True,
                        'values': {timestamp: e_detail_value}
                    }
                    if e_detail_key not in ehm[e_hash]:
                        ehm[e_hash][e_detail_key] = new_historical_dict
                        continue  # new historical var list initialized
                    if not isinstance(ehm[e_hash][e_detail_key], dict) or \
                            'values' not in ehm[e_hash][e_detail_key]:
                        # a non-historical value was made historical
                        #   and this is the first run after that
                        ehm[e_hash][e_detail_key] = new_historical_dict
                        continue
                    # FIXME, this update causes historical values to balloon indefinitely,
                    #   this creates a cache that grows with a multiplier proportional to
                    #   hash count
                    ehm = clean_duplicates_from_(
                        parent_object=ehm,
                        e_hash=e_hash,
                        e_detail_key=e_detail_key
                    )
                    ehm[e_hash][e_detail_key]['values'].update({
                        timestamp: e_detail_value
                    })
                    continue  # existing historical var list updated
                if e_detail_key not in ehm[e_hash]:
                    ehm[e_hash][e_detail_key] = e_detail_value

    def get_files_to_delete(self):
        # convenience
        cds = self.cc.cache['client_data_snapshots']

        # abort if not two snapshots to compare
        enough_snapshots = len(cds) > 1
        if not enough_snapshots:
            return

        # sort snapshot keys to get two most recent
        ts_guids_sorted = sorted(cds)
        cds_after = cds[ts_guids_sorted[-1]]
        cds_before = cds[ts_guids_sorted[-2]]

        if not cds_before:
            # occurs after entries re-added from entry history memory
            return

        # delete all snapshot keys but two most recent
        for ts_guid_sorted in ts_guids_sorted[:-2]:
            del cds[ts_guid_sorted]

        # get files to be deleted
        # check if priorities have changed in two most recent ts_guids
        for e_hash, e_details in cds_after.items():
            priorities_after = cds_after[e_hash]['e_priorities']
            if e_hash not in cds_before:
                continue  # consequence of re-adding from entry memory history
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
                file_to_delete = e_files_data[delete_index]
                files_to_delete.append(file_to_delete)

            # save to client data snapshot
            cds_after[e_hash]['files_to_delete'] = files_to_delete

    def delete_files(self):
        cds_now = self.get_latest_snapshot()

        # loop and delete
        for e_hash, e_details in cds_now.items():
            if 'files_to_delete' not in e_details:
                continue
            files_to_delete = e_details['files_to_delete']
            if not files_to_delete:
                continue
            is_errored = self.query_state_(
                state_query=EStateEnum.errored,
                torrent_hash=e_hash)
            if is_errored:
                e_name = e_details['name']
                print(f'error state at entry : {e_name}')
                self.recheck_and_resume(e_hash)
                continue
            for file_to_delete in files_to_delete:
                self.delete_file(e_hash, file_to_delete)
            self.recheck_and_resume(e_hash)

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

    def remove_parts_files(self, old_age_threshold):
        path_to_parts = self.qbit.app.default_save_path
        items = os.listdir(path_to_parts)
        for item in items:
            starts_with_period = item.startswith('.')
            ends_with_parts = item.endswith('.parts')
            path_to_item = Path(path_to_parts, item)
            age_of_item_hours = get_age_of_(path_to_item)
            item_is_old = age_of_item_hours > old_age_threshold
            if starts_with_period and ends_with_parts and item_is_old:
                path_to_part_file = Path(path_to_parts, item)
                print(f'remove parts file : {path_to_part_file}')
                os.remove(path_to_part_file)

    def init_new_hashes_in_name_maps(self):
        """Init a connection between name maps and entry history memory
        """
        # convenience
        ehm = self.cc.cache['entry_history_memory']

        # read name_maps yaml path from config
        path_to_name_maps = self.config['path']['name_maps']
        if not os.path.exists(path_to_name_maps):
            print(f'path not exist : {path_to_name_maps}')
            exit()
        with open(path_to_name_maps, 'r') as rm_r:
            name_maps = yaml.safe_load(rm_r.read())

        # init all hashes that don't have keys in name_maps
        all_name_map_keys = [key for key in name_maps.keys()]
        keys_to_write = []
        for e_hash, e_details in ehm.items():
            if e_hash not in all_name_map_keys:
                name_map_key = e_hash
                keys_to_write.append(name_map_key)
        with open(path_to_name_maps, 'a') as rm_a:
            # assuming write starts at end of file, start with a newline
            #   since empty lines cause less trouble than overlapping lines
            leading_character = '\n'
            for key_to_write in keys_to_write:
                rm_a.write(leading_character + key_to_write + ':\n')
                leading_character = ''

        # update name_maps with what is on disk
        with open(path_to_name_maps, 'r') as rm_r:
            name_maps = yaml.safe_load(rm_r.read())
        self.config['name_maps'] = name_maps

    def apply_rename_map(self):
        """Rename entries based on name map regex.

        While in development, only execute this function in debug mode.
        Get the required data :
          name_map regex to manually extract new name elements.
          entry_history_memory to reset names

        Reset name to original when :
          1. name_map contains data for the corresponding hash
          2. name_map contains 'testing' key set to True

        Execute rename when :
          1. has not already been renamed?
          2. oldest name is available
          3. name_map for hash exists
          4. name_map contains filled-out regex section

        :return:
        """

        # read name maps from config
        name_maps = self.config['name_maps']
        self.stats['rename']['count_of_name_maps'] = len(name_maps)

        # append oldest names from ehm to name_maps
        ehm_names_oldest = \
            get_original_names(self.cc.cache['entry_history_memory'])
        for e_hash, oldest_name in ehm_names_oldest.items():
            if not isinstance(name_maps[e_hash], dict):
                name_maps[e_hash] = {}
            else:
                name_maps[e_hash].update({'oldest_name': oldest_name})

        # reset names that are still in testing
        self.reset_testing_names_to_original(name_maps=name_maps)

        if not debug:
            print(f'skip rename map, in development')
            return

        if not name_maps:
            print(f'no name_maps file found')
            return

        # iterate over latest snapshot, renaming those with name_maps
        cds_now = self.get_latest_snapshot()
        count_of_renames_performed = 0
        names_skipped = []
        for e_hash, e_details in cds_now.items():
            # build the new name using the old name and name_map regex
            new_name = map_to_new_name_(e_hash=e_hash, name_maps=name_maps)
            name_now = self.qbit.torrents_info(torrent_hash=e_hash).data[0].name
            if new_name:
                self.apply_rename_to_(torrent_hash=e_hash,
                                      new_name=new_name)
            rename_is_successful = name_now == new_name
            if rename_is_successful:
                count_of_renames_performed += 1
                continue

            # to get here the following conditions are met :
            #   1. there is no new name
            names_skipped.append(name_now)

        self.stats['rename']['count_of_renames_performed'] = count_of_renames_performed
        self.stats['rename']['names_skipped'] = names_skipped
        self.announce_rename_statistics()

    def announce_rename_statistics(self, max_names_to_print: int = 0):
        # TODO move this function to the appropriate location or add to
        #   function-level comment
        # FIXME : under active development
        """This function should output information related to the rename(s)
          performed and/or the rename_map's usage. For example, a few lines
          of log entry could look like :

            Name resets performed : 3
            Renames performed : 3
            Name map contains : 8
            Renames not performed : 5
            Names skipped : "file name one", "another file name", "pete"..

          "Names skipped" line could have a "max names printed" limit where
            unlimited if set to 0.

        """
        pass

    def categorize_uncategorized(self):
        pass

    def enforce_download_rates(self):
        pass

    def enforce_upload_rates(self):
        pass

    def enforce_share_ratios(self):
        cds_now = self.get_latest_snapshot()

        # fetch preferences
        enforced_ratio_limit = self.config['qbit']['enforce']['ratio_limit']
        enforced_seeding_time_limit = self.config['qbit']['enforce'][
            'seeding_time_limit']

        for e_hash, e_details in cds_now.items():
            e_ratio_limit = e_details['ratio_limit']
            if e_ratio_limit == enforced_ratio_limit:
                continue
            self.qbit.torrents_set_share_limits(
                torrent_hashes=e_hash,
                ratio_limit=enforced_ratio_limit,
                seeding_time_limit=enforced_seeding_time_limit
            )
            e_name = e_details['name']
            print(f'share ratio set to {enforced_ratio_limit} : {e_name}')

    def pause_completed(self):
        """Originally written to handle the following case :
          An "active" entry with no files to download, but remains un-paused
          for various reasons
        """
        cds_now = self.get_latest_snapshot()
        enforced_ratio_limit = self.config['qbit']['enforce']['ratio_limit']
        # identify hashes with no files selected, pause them
        for e_hash, e_details in cds_now.items():
            # states to skip pause
            is_checking = self.query_state_(
                state_query=EStateEnum.checking,
                torrent_hash=e_hash)
            is_errored = self.query_state_(
                state_query=EStateEnum.errored,
                torrent_hash=e_hash)
            is_paused = self.query_state_(
                state_query=EStateEnum.paused,
                torrent_hash=e_hash)

            if is_checking or is_errored or is_paused:
                continue

            # pause states
            # 1: no files selected
            no_files_selected = e_details['all_delete']
            # 2: ratio exceeded
            e_ratio_limit = e_details['ratio_limit']
            enough_shared = e_ratio_limit > enforced_ratio_limit
            if no_files_selected or enough_shared:
                # TODO confirm paused?
                self.qbit.torrents_pause(torrent_hashes=e_hash)

    def recheck_error_entries(self):
        print(f'checking for error status')
        # convenience
        cds_now = self.get_latest_snapshot()

        for e_hash, e_details in cds_now.items():
            e_state = e_details['state']
            is_errored = self.query_state_(
                state_query=EStateEnum.errored,
                torrent_hash=e_hash)
            if is_errored:
                self.qbit.torrents_recheck(torrent_hashes=e_hash)

    def resume_paused(self):
        all_entries = self.qbit.torrents_info()
        for entry in all_entries:
            is_complete = self.query_state_(
                state_query=EStateEnum.complete,
                torrent_hash=entry.hash
            )
            if is_complete:
                continue  # avoid resuming completed
            is_paused = self.query_state_(
                state_query=EStateEnum.paused,
                torrent_hash=entry.hash)
            if is_paused:
                print(f'resume : {entry.name}')
                self.qbit.torrents_resume(entry.hash)

    def reset_testing_names_to_original(self, name_maps):
        ehm = self.cc.cache['entry_history_memory']

        # skip over name_maps that aren't in testing
        count_of_names_reset = 0
        for e_hash, name_map in name_maps.items():
            if not name_map:
                continue
            if 'testing' not in name_map:
                continue
            if not name_map['testing']:
                continue
            # perform name reset
            # get oldest name for this e_hash
            if e_hash in ehm:
                name_history = ehm[e_hash]['name']['values']
                oldest_name = name_history[sorted(name_history, reverse=True)[-1]]
            else:
                continue

            # perform rename
            self.qbit.torrents_rename(torrent_hash=e_hash,
                                      new_torrent_name=oldest_name)
            # confirm rename was performed?
            # FIXME name_now to torrent.name
            name_now = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].name
            # FIXME any bug potential here? does a name_before make any sense?
            name_reset_was_performed = oldest_name == name_now
            if name_reset_was_performed:
                count_of_names_reset += 1

        self.stats['rename']['count_of_names_reset'] = count_of_names_reset

    def resurrect_entry_history_memory(self, category='resurrected'):
        ehm = self.cc.cache['entry_history_memory']
        for e_hash, e_details in ehm.items():
            magnet = e_details['magnet_uri']
            if not magnet:
                continue
            self.add_entry(magnet=magnet,
                           category=category)

    # FUNCTION TIER 04, Lower-level program flow
    # add_entry(), apply_rename_to(), delete_file(), get_latest_snapshot(),
    #   query_state_(), read_guid_offset(), read_name_maps(),
    #   recheck_and_resume()

    def add_entry(self, magnet, category, timeout=5):
        # check if already added
        entry_magnets = [entry['magnet_uri'] for entry in self.qbit.torrents_info()]
        already_added = magnet in entry_magnets
        if already_added:
            return

        # attempt to add
        successfully_added, timeout = False, False
        start_time = time()
        while not successfully_added and not timeout:
            time_elapsed = time() - start_time
            timeout = time_elapsed > timeout
            self.qbit.torrents_add(
                category=category,
                download_limit=DataRate.KiB_per_sec * 10,
                ratio_limit=0.01,
                urls=magnet,
            )
            sleep(1)
            entry_magnets = [entry['magnet_uri'] for entry in self.qbit.torrents_info()]
            successfully_added = magnet in entry_magnets
        if successfully_added:
            print(f'successfully added : {magnet}')
        if timeout:
            print(f'timeout adding : {magnet}')

    def apply_rename_to_(self, torrent_hash, new_name, timeout_sec=3):
        # update name
        timeout_sec = timeout_debug if debug else timeout_sec
        name_changed, timeout = False, False
        start_time = time()
        while not name_changed and not timeout:
            time_elapsed = time() - start_time
            timeout = time_elapsed > timeout_sec
            self.qbit.torrents_rename(torrent_hash=torrent_hash,
                                      new_torrent_name=new_name)
            sleep(1)
            entry_name = self.qbit.torrents_info(
                torrent_hashes=torrent_hash)[0].name
            if entry_name == new_name:
                name_changed = True

    def delete_file(self, e_hash, file_data, timeout_sec=15):
        timeout_sec = timeout_debug if debug else timeout_sec
        e_info = self.qbit.torrents_info(torrent_hashes=e_hash)
        f_name = file_data['name']
        content_path = e_info.data[0].content_path

        # pause entry
        e_state = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].state
        is_paused = self.query_state_(
            state_query=EStateEnum.paused,
            torrent_hash=e_hash)
        is_completed = self.query_state_(
            state_query=EStateEnum.complete,
            torrent_hash=e_hash)
        if not is_paused and not is_completed:
            self.qbit.torrents_pause(torrent_hashes=e_hash)

            # wait, verify paused
            is_paused, timeout, start_time = False, False, time()
            print(f'pausing {e_hash} to delete {f_name}')
            while not is_paused and not timeout:
                timeout = time() - start_time > timeout_sec
                if timeout:
                    print(f'pause timed out')
                    exit()
                is_paused = self.query_state_(
                    state_query=EStateEnum.paused,
                    torrent_hash=e_hash)
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
        if os.path.exists(path_to_file):
            try:
                print(f'delete from disk : {path_to_file}')
                os.remove(path_to_file)
            except Exception as exc:
                print(f'failed to delete file : {exc}')

    def get_latest_snapshot(self):
        cds = self.cc.cache['client_data_snapshots']
        snapshot = cds[sorted(cds)[-1]]
        return snapshot

    def query_state_(self, state_query, torrent_hash: str):
        # convenience
        e_info = self.qbit.torrents_info(torrent_hashes=torrent_hash)
        state_enum = e_info.data[0].state_enum

        if state_query is EStateEnum.checking:
            return state_enum.is_checking
        if state_query is EStateEnum.complete:
            return state_enum.is_complete
        if state_query is EStateEnum.download:
            return state_enum.is_downloading
        if state_query is EStateEnum.errored:
            return state_enum.is_errored
        if state_query is EStateEnum.paused:
            return state_enum.is_paused
        if state_query is EStateEnum.uploading:
            return state_enum.is_uploading

    def read_guid_offset(self):
        guid_offset = self.config['qbit']['rename']['offset']
        if not guid_offset:
            print(f'no value for guid offset in config')
            return Default.guid_offset
        return guid_offset

    def recheck_and_resume(self, e_hash, timeout_sec=15):
        timeout_sec = timeout_debug if debug else timeout_sec
        e_name = self.qbit.torrents_info(torrent_hashes=e_hash).data[0].name

        # force recheck
        print(f'rechecking {e_name}')
        self.qbit.torrents_recheck(torrent_hashes=e_hash)

        # wait for recheck to complete
        is_checking = True
        is_timeout, start_time = False, time()
        while is_checking and not is_timeout:
            is_timeout = time() - start_time > timeout_sec
            if is_timeout:
                print(f'checking timed out')
                exit()
            is_checking = self.query_state_(
                state_query=EStateEnum.checking,
                torrent_hash=e_hash)

        # resume
        self.qbit.torrents_resume(torrent_hashes=e_hash)


# FUNCTION TIER 05, Class-external-level program flow
# add_efd_files_data_to_(), create_new_cache(), get_category_from(),
#   get_timestamp(), main_loop_wait(), qbit_is_running(),
#   query_qbit_application_wait_()

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


def create_new_cache(path_to_cache):
    print(f'file not exist : {path_to_cache}')
    try:
        print(f'attempt create file : {path_to_cache}')
        with open(path_to_cache, 'w') as new_cache:
            new_cache.write('{}')
    except Exception as exc:
        print(f'exception creating new cache : {exc}')
        raise exc


def get_category_from_(entry):
    category = entry['category']
    if not category:
        return 'Uncategorized'
    return category


def clean_duplicates_from_(parent_object, e_hash, e_detail_key):
    ipo = immutable_parent_object = copy.deepcopy(parent_object)
    immutable_values = ipo[e_hash][e_detail_key]['values']
    # The goal is to compare the object to itself, removing duplicates
    # Make a copy of the object to iterate over, editing the original
    # Create a list that will hold timestamps associated with unique values
    #   This list will be used to prevent deletion of these unique entries
    # From the copy, get the oldest value, collect the associated timestamp
    ts_kv_for_unique_vals = {}
    for timestamp, value in immutable_values.items():
        if value is None:
            continue  # In case of None

        # Collect unique entries, this collection is used to prevent deletion
        if value not in list(ts_kv_for_unique_vals.values()):
            ts_kv_for_unique_vals.update({timestamp: value})

    mutable_values = parent_object[e_hash][e_detail_key]['values']
    for timestamp, value in immutable_values.items():
        if timestamp not in list(ts_kv_for_unique_vals.keys()):
            del mutable_values[timestamp]

    return parent_object


def get_original_names(ehm):
    names_oldest = {}
    for e_hash, e_details in ehm.items():
        name_timestamps = e_details['name']['values']
        ns = name_timestamps
        name_oldest = ns[sorted(ns)[-1]]
        names_oldest.update({e_hash: name_oldest})
    return names_oldest


def get_timestamp():
    t_format = "%Y_%m%d_%H%M_%S"
    t_now = strftime(t_format, gmtime())
    return t_now


def main_loop_wait(run_frequency):
    run_frequency = run_frequency_debug if debug else run_frequency
    notification_interval = 30
    wait_time = 1 / run_frequency
    while wait_time:
        if not wait_time % notification_interval or \
                wait_time < 4:
            print(f'{wait_time} seconds until next loop{debug_warning}')
        sleep(1)
        if not wait_time:
            return
        wait_time -= 1


def qbit_is_running():
    for running_process in psutil.process_iter():
        if QbitProcess.name in running_process.name():
            return True
    print(f'qbit process not running, doing nothing')
    return False
