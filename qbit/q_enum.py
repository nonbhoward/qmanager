class EntryState:
    download = 'downloading'
    error = 'error'
    paused_dn = 'pausedDL'
    paused_up = 'pausedUP'
    stalled = 'stalledDL'
    # convenience
    stopped = 'paused'


class FilePriority:
    not_download = 0
    download = 1


class GroupKeyIndex:
    to_delete = [0]
    to_keep = [1, 2]

class HistoricalKeys:
    # all available keys
    # 'files_to_delete', 'efd_files_data', 'e_priorities', 'all_delete',
    # 'added_on', 'amount_left', 'auto_tmm', 'availability', 'category',
    # 'completed', 'completion_on', 'content_path', 'dl_limit', '_______',
    # 'download_path', 'downloaded', 'downloaded_session', 'eta',
    # 'f_l_piece_prio', 'force_start', 'hash', 'infohash_v1', 'infohash_v2',
    # 'last_activity', 'magnet_uri', 'max_ratio', 'max_seeding_time', '____',
    # 'num_complete', 'num_incomplete', 'num_leechs', 'num_seeds', 'priority',
    # 'progress', 'ratio', 'ratio_limit', 'save_path', 'seeding_time',
    # 'seeding_time_limit', 'seen_complete', 'seq_dl', 'size', '_____',
    # 'super_seeding', 'tags', 'time_active', 'total_size', 'tracker',
    # '______________', 'up_limit', 'uploaded', 'uploaded_session', '_______'
    keys = [
        'content_path',
        'dlspeed',
        'name',
        'state',
        'trackers_count',
        'upspeed'
    ]
