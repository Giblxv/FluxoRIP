"""Write derived JSON only to a new path, never replacing an existing inode.

This intentionally does not provide an overwrite option. No input file is opened
for writing; O_EXCL protects hardlinks, symlinks and pre-existing outputs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def write_new_json(destination, data):
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            fd = -1
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
    except BaseException:
        if fd >= 0:
            os.close(fd)
        # Leave a partial file in place for inspection; never unlink a path
        # that could have been substituted by another process.
        raise
