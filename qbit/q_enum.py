class DataRate:
    KiB_per_sec = 1024


class ENameType:
    none = ''
    series = 'series'


class EStateEnum:
    checking = 'checking'
    complete = 'complete'
    download = 'downloading'
    errored = 'errored'
    paused = 'paused'
    uploading = 'uploading'


class FilePriority:
    not_download = 0
    download = 1


class HistoricalKeys:
    # All available keys
    # 'files_to_delete', 'efd_files_data', 'e_priorities', 'all_delete',
    # 'added_on', 'amount_left', 'auto_tmm', 'availability', '________',
    # 'completed', 'completion_on', 'content_path', 'dl_limit', '_______',
    # 'download_path', 'downloaded', 'downloaded_session', 'eta',
    # 'f_l_piece_prio', 'force_start', 'hash', 'infohash_v1', 'infohash_v2',
    # 'last_activity', 'magnet_uri', 'max_ratio', 'max_seeding_time', '____',
    # 'num_complete', 'num_incomplete', 'num_leechs', 'num_seeds', 'priority',
    # 'progress', 'ratio', 'ratio_limit', 'save_path', 'seeding_time',
    # 'seeding_time_limit', 'seen_complete', 'seq_dl', 'size', '_____',
    # 'super_seeding', 'tags', 'time_active', 'total_size', 'tracker',
    # '______________', 'up_limit', 'uploaded', 'uploaded_session', '_______'
    active = [
        'category',
        'content_path',
        'dlspeed',
        'name',
        'progress',
        'state',
        'trackers_count',
        'upspeed'
    ]


class PartsAge:
    one_second = 1 / 3600
    one_day = 24
    one_week = 168


class QbitProcess:
    name = 'qbit'


class RunFrequency:
    per_minute = 1 / 60
    per_fifth_minute = 1 / 300
    per_tenth_minute = 1 / 600
    per_quarter_hour = 1 / 900
    per_half_hour = 1 / 1800
    per_hour = 1 / 3600


class UserPrompt:
    debug_flag_warning = ', DISABLE DEBUG FLAG!'

class Default:
    guid_offset = 5
