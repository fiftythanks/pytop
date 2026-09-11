from dataclasses import dataclass
from enum import Enum


# Process state (`proc_pid_status(5)`)
class State(Enum):
    RUNNING = 'R'
    SLEEPING = 'S'
    DISK_SLEEP = 'D'
    STOPPED = 'T'
    TRACING_STOP = 't'
    ZOMBIE = 'Z'
    DEAD = 'X'
    # There’s no such state in the documentation, but it appears in some process
    # statuses.
    IDLE = 'I'


@dataclass
class Process:
    """Dataclass holding all the stats the program keeps for each process.

    `None` values mean that there was an error while trying to access the
    corresponding file, e.g. a permission error or file-not-found.

    Attributes:
        `pid`, `name`, `ppid`, `threads`, `vmrss`, `state`: Equivalent to the
    corresponding values from `/proc/[pid]/status`. More information can be
    accessed on the `proc_pid_status(5)` manpage.
        `rchar` and `wchar`: Equivalent to the corresponding values from
    `/proc/[pid]/io`. Read `proc_pid_io(5)` for more details.
        cmd: The command that started the process.
        effective_user_name: The username corresponding to the `euid`, the second
    UID in the `uid` value from `/proc/[pid]/status`.
        uptime_ms: The time the process has been running.
    """

    pid: int
    name: str | None = None
    ppid: int | None = None
    cmd: str | None = None
    threads: int | None = None
    effective_user_name: str | None = None
    vmrss: int | None = None
    cpu_usage_percent: float | None = None
    state: State | None = None
    uptime_ms: float | None = None
    read_bytes: int | None = None
    write_bytes: int | None = None
