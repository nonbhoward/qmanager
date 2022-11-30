class EntryState:
    completed = 'pausedUP'
    paused = 'pausedDL'
    stopped = 'paused'


class FilePriority:
    not_download = 0
    download = 1


class GroupKeyIndex:
    to_delete = [0]
    to_keep = [1, 2]
