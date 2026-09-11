import os
import pwd
from pathlib import Path
from typing import Protocol

from pytop.shared.process import Process, State


class GetProcesses(Protocol):
    def __call__(self) -> dict[int, Process]: ...


def create_process_monitor(proc_dir: Path = Path('/proc')) -> GetProcesses:
    # Keys correspond to PIDs and values (tuples) hold CPU and process ticks
    # respectively.
    ticks: dict[int, tuple[int, int]] = {}

    def get_processes():
        """Returns a list of processes currently running.

        This function assumes that files `/proc/[pid]/status`, `/proc/[pid]/io`,
        `/proc/[pid]/cmdline` strictly adhere to `proc_pid_status(5)`,
        `proc_pid_io(5)`, `proc_pid_cmdline(5)` manpages. The only exception is that
        processes are allowed to have a non-standard state “I (idle)”.

        The function doesn’t check that the passed path is exactly `/proc`. The only
        important characteristic of the path is that it must conform to the
        mentioned docs.

        Attributes:
            proc_dir: The path to `/proc`.
        """

        nonlocal ticks
        processes: dict[int, Process] = {}
        cpu_ticks = 0

        # Calculate the CPU ticks (used by all cores) by parsing `/proc/stat`.
        try:
            proc_stat_file = proc_dir / 'stat'
            stat = proc_stat_file.read_text()
            cpu_stat = stat.splitlines()[0]

            for word in cpu_stat.split():
                if word == 'cpu':
                    continue

                cpu_ticks += int(word)

        except (PermissionError, FileNotFoundError, ValueError):
            pass

        cpu_uptime_seconds = 0.0

        # Get the CPU uptime
        try:
            proc_uptime_file = proc_dir / 'uptime'
            cpu_uptime_seconds = float(proc_uptime_file.read_text().split()[0])

        except (PermissionError, FileNotFoundError, ValueError):
            pass

        for subdir in proc_dir.iterdir():
            if subdir.is_dir() and subdir.name.isdigit():
                proc_pid_dir = subdir
                pid = int(proc_pid_dir.name)
                process = Process(pid)

                # /proc/[pid]/status
                try:
                    proc_pid_status_file = proc_pid_dir / 'status'
                    process_status = proc_pid_status_file.read_text()

                    for line in process_status.splitlines():
                        if line.startswith('Name:'):
                            try:
                                process.name = line.split(maxsplit=1)[1]
                            except IndexError:
                                pass
                        elif line.startswith('PPid:'):
                            try:
                                process.ppid = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('Threads:'):
                            try:
                                process.threads = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('Uid:'):
                            # UID must contain 4 IDs. If it doesn’t, something is
                            # wrong and it’s safer to fallback to `None`.
                            uid_split = line.split()
                            if len(uid_split) != 5:
                                pass
                            else:
                                euid = uid_split[2]
                                try:
                                    process.effective_user_name = pwd.getpwuid(
                                        int(euid)
                                    ).pw_name
                                # Do not crash if the user doesn’t exist any longer or
                                # something of the kind happens.
                                except KeyError:
                                    process.effective_user_name = euid
                                except ValueError:
                                    pass
                        elif line.startswith('VmRSS:'):
                            try:
                                process.vmrss = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('State:'):
                            try:
                                process.state = State(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                except FileNotFoundError:
                    continue
                # Permission errors are handled gracefully in Btop, either
                # displaying an empty space or 0 as the value.
                except PermissionError:
                    pass

                # /proc/[pid]/cmdline
                try:
                    cmdline = (proc_pid_dir / 'cmdline').read_text()
                    process.cmd = cmdline.replace('\0', ' ').strip()
                except (PermissionError, FileNotFoundError):
                    pass

                # /proc/[pid]/io
                try:
                    proc_pid_io_file = proc_pid_dir / 'io'
                    io = proc_pid_io_file.read_text()

                    for line in io.splitlines():
                        if line.startswith('read_bytes:'):
                            process.read_bytes = int(line.split()[1])
                        elif line.startswith('write_bytes:'):
                            process.write_bytes = int(line.split()[1])
                except (
                    PermissionError,
                    FileNotFoundError,
                    ValueError,
                    IndexError,
                ):
                    pass

                # CPU Usage and Process Uptime
                process_ticks = 0
                starttime: int = 0

                try:
                    proc_pid_stat_file = proc_pid_dir / 'stat'
                    stat = proc_pid_stat_file.read_text()

                    # Cut off the PID and the name of the process, which is
                    # included in parentheses.
                    last_closing_parenthesis_index = stat.rfind(')')
                    stat_starting_from_state = stat[
                        last_closing_parenthesis_index + 1 :
                    ]

                    for i, word in enumerate(stat_starting_from_state.split()):
                        # Only `utime`, `stime`, `cutime`, `cstime`,
                        # `starttime`, `guest_time` and `cguest_time` are of
                        # interest to us.
                        if (
                            i < 11
                            or i >= 15
                            and i != 19
                            and i != 40
                            and i != 41
                        ):
                            continue

                        if i == 19:
                            starttime = int(word)
                            continue

                        process_ticks += int(word)

                except (PermissionError, FileNotFoundError, ValueError):
                    pass

                if pid in ticks:
                    delta_cpu_ticks = cpu_ticks - ticks[pid][0]
                    delta_process_ticks = process_ticks - ticks[pid][1]

                    cores_number = os.cpu_count()
                    if cores_number is None:
                        cores_number = 1

                    if delta_cpu_ticks == 0:
                        process.cpu_usage_percent = 0.0
                    else:
                        # IRIX mode where full capacity is 100% × amount of
                        # cores
                        process.cpu_usage_percent = round(
                            (delta_process_ticks / delta_cpu_ticks)
                            * 100
                            * cores_number,
                            2,
                        )

                    ticks[pid] = (cpu_ticks, process_ticks)
                else:
                    ticks[pid] = (cpu_ticks, process_ticks)
                    process.cpu_usage_percent = 0

                if cpu_uptime_seconds <= 0:
                    process.uptime_ms = 0
                else:
                    tick_length_hz = os.sysconf('SC_CLK_TCK')
                    process.uptime_ms = round(
                        (cpu_uptime_seconds - starttime / tick_length_hz)
                        * 1_000,
                        2,
                    )

                processes[pid] = process

        # Cleanup
        for key in list(ticks.keys()):
            if key not in processes:
                del ticks[key]

        return processes

    return get_processes
