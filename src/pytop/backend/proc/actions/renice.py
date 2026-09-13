import os

from pytop.backend.proc.actions.errors import (
    ProcActionProcessLookupError,
    RenicePermissionError,
)


def renice(pid: int, priority: int) -> bool:
    if priority < -20 or priority >= 20:
        raise ValueError('Incorrect priority!')

    try:
        os.setpriority(which=os.PRIO_PROCESS, who=pid, priority=priority)
    except PermissionError:
        raise RenicePermissionError(pid)
    except ProcessLookupError:
        raise ProcActionProcessLookupError(pid)

    return True
