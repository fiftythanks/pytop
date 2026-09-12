import os


def renice(pid: int, priority: int) -> bool:
    if priority < -20 or priority >= 20:
        raise ValueError('Incorrect priority!')

    # TODO: Handle edge cases when integration testing
    os.setpriority(which=os.PRIO_PROCESS, who=pid, priority=priority)

    return True
