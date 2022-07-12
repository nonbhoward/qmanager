# python lib imports
from re import match
from time import sleep
# 3rd party imports
import copy

import qbittorrentapi
# project imports


class ResultKey:
    link = 'descrLink'
    leech_count = 'nbLeechers'
    name = 'fileName'
    seed_count = 'nbSeeders'
    size = 'fileSize'
    url_file = 'fileUrl'
    url_site = 'siteUrl'


class SearchStatus:
    running = 'Running'
    stopped = 'Stopped'


class QManager:
    def __init__(self, app_config,
                 search_memory,
                 loops_per_run=1,
                 delay_btw_loops=60):
        """
        interface to the qbittorrent client
        :param app_config: project wide configuration
        :param search_memory: project search memory
        :param loops_per_run: count of how many times looped events in
                 self.run() will occur
        :param delay_btw_loops: the delay between looped events
        """
        self._client = None
        self._search_jobs = None
        self._entry_guids = None
        self._entry_count = None
        self._app_config = app_config
        self._search_memory = search_memory
        self._search_queue = app_config['search queue']
        self._search_regex = app_config['search regex']
        self._loops_per_run = loops_per_run
        self._delay_btw_loops = delay_btw_loops
        self._authenticate_client()

    def run(self):
        """
        all management tasks executed by this class
        :return: None
        """
        loops_remaining = self._loops_per_run
        delay_btw_loops = self._delay_btw_loops
        while loops_remaining:
            print(f"starting new loop..")
            self._populate_entry_guids()
            self._queued_search_start()
            self._process_search_results(
                result_limit=10
            )
            self._add_qualifying_entries(limit_dn=1,
                                         limit_up=1)
            self._rename_entries()
            self._resume_unresolved_entries()
            self._curate_newly_resolved_entries()
            self._pause_unresolved_entries()
            loops_remaining -= 1
            execute_delay(delay_seconds=delay_btw_loops)

    def get_entry_count(self):
        entry_count = len(self.get_entry_info())
        return entry_count

    def get_entry_info(self):
        client = self._client
        entry_info = client.torrents.info()
        return entry_info

    def _authenticate_client(self, host='localhost',
                             port=8080,
                             username=None,
                             password=None):
        """
        authenticate with the web ui
        :param host: web ui address
        :param port: web ui port
        :param username: if required, the username
        :param password: if required, the password
        :return: None, save authenticated client to class
        """
        client = qbittorrentapi.Client(
            host=host,
            port=port,
            username=username,
            password=password
        )
        self._client = client

    def _populate_entry_guids(self):
        """
        get the guid (hash) from each of the entries
        :return: None, save list of guids to class
        """
        client = self._client
        entries = client.torrents.info()
        entry_guids = []
        for entry in entries:
            entry_guids.append(entry.info.hash)
        if not entry_guids:
            print(f"there are no entries")
            return
        self._entry_guids = entry_guids
        self._entry_count = len(entry_guids)

    def _queued_search_start(self):
        """
        changes a search status from queued to running
        :return:
        """
        client = self._client
        search_jobs = copy.deepcopy(self._search_jobs)
        if not search_jobs:
            search_jobs = dict()
        for search_label, search_details in self._search_queue.items():
            search_terms = search_details.get('search terms').split(',')
            for search_term in search_terms:
                if not search_term:
                    continue
                search_job = client.search_start(pattern=search_term,
                                                 plugins='all',
                                                 category='all')
                search_key = search_term + '_' + str(search_job.id)
                search_jobs.update({
                    search_key: {
                        'search_job': search_job,
                        'search_details': search_details
                    }})
        self._search_jobs = search_jobs

    def _process_search_results(self, result_limit=10):
        """
        get status from running searches and save search results
        :return:
        """
        client = self._client
        search_jobs = copy.deepcopy(self._search_jobs)
        if not search_jobs:
            return
        for search_label, search_details in self._search_jobs.items():
            search_id = search_details['search_job'].id
            search_status = get_search_status(client, search_id)
            search_jobs[search_label].update({
                'search_status': search_status
            })
            if search_status == SearchStatus.stopped:
                search_results = client.search_results(search_id=search_id,
                                                       limit=result_limit)
                search_jobs[search_label].update({
                    'search_results': search_results
                })
        self._search_jobs = search_jobs

    def _add_qualifying_entries(self, add_paused=True,
                                limit_up=0,
                                limit_dn=0):
        search_jobs = self._search_jobs
        search_queue = self._search_queue
        for search_label, search_job in search_jobs.items():
            if 'search_results' not in search_job:
                continue
            search_results = search_jobs[search_label]['search_results']
            for search_result in search_results['results']:
                count_before = self.get_entry_count()
                search_regex = self._get_search_regex_from(search_queue)
                self._add_url_file(search_result=search_result,
                                   add_paused=add_paused,
                                   limit_up=limit_up,
                                   limit_dn=limit_dn,
                                   search_regex=search_regex)
                count_after = self.get_entry_count()
                add_successful = count_before != count_after

    def _add_url_file(self, search_result,
                      add_paused,
                      limit_up,
                      limit_dn,
                      search_regex):
        client = self._client
        search_result_name = search_result[ResultKey.name]
        if regex_matches_for(search_result_name, search_regex):
            url_file = search_result[ResultKey.url_file]
            client.torrents.add(urls=url_file,
                                is_paused=add_paused,
                                download_limit=limit_dn,
                                upload_limit=limit_up)

    def _get_search_regex_from(self, search_label):
        # FIXME, rethink how the keying works here
        #  search_label has value "linux iso search" in config
        #  search_label has value "linux_1234567890" in queue
        app_config = self._app_config
        search_queue = app_config[search_label]
        search_regex = search_queue[search_label]['filter']
        return search_regex

    def _rename_entries(self):
        client = self._client
        pass

    def _resume_unresolved_entries(self):
        pass

    def _curate_newly_resolved_entries(self):
        pass

    def _pause_unresolved_entries(self):
        pass


def execute_delay(delay_seconds):
    one_second = 1
    for delay_second in range(delay_seconds):
        print(f"waiting {delay_seconds} seconds, {delay_second}..")
        sleep(one_second)


def get_search_status(client, search_id):
    search_status = client.search_status(search_id=search_id)
    search_status = search_status.data[0].status
    return search_status


def get_key_from_result(result: dict,
                        key: ResultKey) -> str:
    if key not in ResultKey:
        print(f"invalid result key attribute")
        exit()
    return result[key]


def regex_matches_for(search_result_name, search_filter):
    result_name_match = match(search_filter, search_result_name)
    return result_name_match
