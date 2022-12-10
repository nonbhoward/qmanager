class EntryState:
    completed = 'pausedUP'
    download = 'downloading'
    error = 'error'
    paused = 'pausedDL'
    stalled = 'stalledDL'


class FilePriority:
    not_download = 0
    download = 1


class GroupKeyIndex:
    to_delete = [0]
    to_keep = [1, 2]
