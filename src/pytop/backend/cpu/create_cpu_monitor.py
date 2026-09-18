import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pytop.backend.cpu.exceptions import (
    ProcCpuinfoFileNotFoundWarning,
    ProcCpuinfoIndexWarning,
    ProcCpuinfoPermissionWarning,
    ProcLoadavgFileNotFoundWarning,
    ProcLoadavgIndexWarning,
    ProcLoadavgPermissionWarning,
    ProcLoadavgValueWarning,
    ProcStatFileNotFoundWarning,
    ProcStatIndexWarning,
    ProcStatPermissionWarning,
    ProcStatValueWarning,
    ProcUptimeFileNotFoundWarning,
    ProcUptimeIndexWarning,
    ProcUptimePermissionWarning,
    ProcUptimeValueWarning,
)


@dataclass(frozen=True)
class TmpCpuStats:
    name: str | None
    uptime_sec: float | None
    load_avg_1min: float | None
    load_avg_5min: float | None
    load_avg_15min: float | None
    usage_percent: float | None


class GetCpuStats(Protocol):
    def __call__(self) -> TmpCpuStats: ...


def create_cpu_monitor(proc_path: Path = Path('/proc')) -> GetCpuStats:
    # Across all CPUs.
    previous_ticks = {'total': 0, 'used': 0}

    # Paths to files to parse.
    proc_uptime_path = proc_path / 'uptime'
    proc_loadavg_path = proc_path / 'loadavg'
    proc_cpuinfo_path = proc_path / 'cpuinfo'
    proc_stat_path = proc_path / 'stat'

    def get_cpu_stats() -> TmpCpuStats:
        """Parse system files and get a snapshot of CPU stats.

        This function creates a snapshot of all CPU-relevant stats at the
        moment in the form of a dictionary, where keys are stat names and
        values are their values, with the exception of CPU core stats. Those
        are structured in the same way, but each core has its own snapshot
        and all core snapshots are inside a dictionary where keys are core IDs
        and values are the core-snapshot dictionaries. Finally, this dictionary
        of core snapshots is referenced as `'core_stats'` in the `'cpu_stats'`
        snapshot `get_cpu_stats()` returns.

        To illustrate:

        ```text
        cpu_stats
            load_avg_5min
            core_stats
                freq
                ...
            uptime
            ...
        ```

        Parses:
            - `/proc/uptime`
            - `/proc/loadavg`
            - `/proc/cpuinfo`
            - `/proc/stat`

        Gets and calculates:
            - System uptime (in seconds)
            - CPU load average for 1, 5 and 15 min
            - CPU name (e.g. Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz)
            - Total CPU usage in per cent

        Note: Whenever a file is absent, the corresponding stats are assigned
        `None` values.
        """

        # =====================================================================
        # UPTIME
        # =====================================================================
        uptime_sec = None

        if proc_uptime_path.exists():
            try:
                proc_uptime_content = proc_uptime_path.read_text()
                uptime_sec_values = proc_uptime_content.split()
                system_uptime_sec = uptime_sec_values[0]
                uptime_sec = float(system_uptime_sec)
            except PermissionError:
                warnings.warn(ProcUptimePermissionWarning(proc_uptime_path))
            except IndexError as err:
                # TODO: Implement a more helpful warning for predictable cases.
                warnings.warn(ProcUptimeIndexWarning(message=str(err)))
            except ValueError as err:
                # TODO: Implement a more helpful warning for predictable cases.
                warnings.warn(ProcUptimeValueWarning(message=str(err)))
        else:
            warnings.warn(ProcUptimeFileNotFoundWarning(proc_uptime_path))

        # =====================================================================
        # LOAD AVERAGE
        # =====================================================================
        load_avg_1min = None
        load_avg_5min = None
        load_avg_15min = None

        if proc_loadavg_path.exists():
            try:
                proc_loadavg_content = proc_loadavg_path.read_text()
                loadavg_values = proc_loadavg_content.split()
                load_avg_1min = float(loadavg_values[0])
                load_avg_5min = float(loadavg_values[1])
                load_avg_15min = float(loadavg_values[2])
            except PermissionError:
                warnings.warn(ProcLoadavgPermissionWarning(proc_loadavg_path))
            except IndexError as err:
                # TODO: Implement a more helpful warning for predictable cases.
                warnings.warn(ProcLoadavgIndexWarning(message=str(err)))
            except ValueError as err:
                # TODO: Implement a more helpful warning for predictable cases.
                warnings.warn(ProcLoadavgValueWarning(message=str(err)))
        else:
            warnings.warn(ProcLoadavgFileNotFoundWarning(proc_loadavg_path))

        # =====================================================================
        # CPU NAME
        # =====================================================================
        name = None

        if proc_cpuinfo_path.exists():
            try:
                proc_cpuinfo_content = proc_cpuinfo_path.read_text()
                for line in proc_cpuinfo_content.splitlines():
                    if line.startswith('model name'):
                        name = line.split(':')[1].strip()
                        break
            except PermissionError:
                warnings.warn(ProcCpuinfoPermissionWarning(proc_cpuinfo_path))
            except IndexError as err:
                # TODO: Implement a more helpful warning for predictable cases.
                warnings.warn(ProcCpuinfoIndexWarning(message=str(err)))

        else:
            warnings.warn(ProcCpuinfoFileNotFoundWarning(proc_cpuinfo_path))

        # =====================================================================
        # USAGE PER CENT (ALL CPU’S)
        # =====================================================================
        usage_percent = None

        if proc_stat_path.exists():
            try:
                stats = []

                proc_stat_content = proc_stat_path.read_text()
                for line in proc_stat_content.splitlines():
                    if line.startswith('cpu'):
                        stats = line.split()
                        break

                user_ticks = int(stats[1])
                nice_ticks = int(stats[2])
                system_ticks = int(stats[3])
                idle_ticks = int(stats[4])
                iowait_ticks = int(stats[5])
                irq_ticks = int(stats[6])
                softirq_ticks = int(stats[7])
                steal_ticks = int(stats[8])

                # `guest` and `guest_nice` are redundant for calculating total CPU
                # usage since they are already included in `user` and `nice`.
                # guest_ticks = int(stats[9])
                # guest_nice_ticks = int(stats[10])

                not_used_ticks = idle_ticks + iowait_ticks
                used_ticks = sum(
                    [
                        user_ticks,
                        nice_ticks,
                        system_ticks,
                        irq_ticks,
                        softirq_ticks,
                        steal_ticks,
                    ]
                )
                total_ticks = not_used_ticks + used_ticks

                nonlocal previous_ticks
                if previous_ticks['total'] == 0:
                    previous_ticks['total'] = total_ticks
                    previous_ticks['used'] = used_ticks

                    # Without the delta, it is impossible to calculate total CPU
                    # usage. And in this branch we can’t have delta yet, only the
                    # initial value which will be subtracted from the value we get
                    # in the next `get_cpu_stats` call. Therefore, `usage_percent`
                    # stays `None`.
                else:
                    used_ticks_delta = used_ticks - previous_ticks['used']
                    total_ticks_delta = total_ticks - previous_ticks['total']
                    usage_percent = (used_ticks_delta / total_ticks_delta) * 100

                    previous_ticks['used'] = used_ticks
                    previous_ticks['total'] = total_ticks
            except PermissionError:
                warnings.warn(ProcStatPermissionWarning(proc_stat_path))
            except ValueError as err:
                warnings.warn(ProcStatValueWarning(message=str(err)))
            except IndexError as err:
                warnings.warn(ProcStatIndexWarning(message=str(err)))
        else:
            warnings.warn(ProcStatFileNotFoundWarning(proc_stat_path))

        return TmpCpuStats(
            name=name,
            uptime_sec=uptime_sec,
            load_avg_1min=load_avg_1min,
            load_avg_5min=load_avg_5min,
            load_avg_15min=load_avg_15min,
            usage_percent=usage_percent,
        )

    return get_cpu_stats
