import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pytop.backend.cpu.exceptions import (
    PowerTelemetrySensorNotFoundWarning,
    PowerTelemetrySensorPermissionWarning,
    PowerTelemetrySensorValueWarning,
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
from pytop.backend.cpu.power_telemetry.discover_power_telemetry_sensors import (
    discover_power_telemetry_sensors,
)


@dataclass(frozen=True)
class TmpCpuStats:
    name: str | None
    uptime_sec: float | None
    load_avg_1min: float | None
    load_avg_5min: float | None
    load_avg_15min: float | None
    usage_percent: float | None
    power_consumption_watt: dict[Path, float | None]


class GetCpuStats(Protocol):
    def __call__(self) -> TmpCpuStats: ...


def create_cpu_monitor(
    proc_path: Path = Path('/proc'), sys_path: Path = Path('/sys')
) -> GetCpuStats:
    # Across all CPUs.
    previous_ticks = {'total': 0, 'used': 0}
    # Maps the sensor `Path` to a tuple of `(previous_uj_value, previous_timestamp).`
    previous_energy: dict[Path, tuple[int, int]] = {}
    # TODO: Add `previous_power` when you implement HWMON search.

    # Paths to files to parse.
    proc_uptime_path = proc_path / 'uptime'
    proc_loadavg_path = proc_path / 'loadavg'
    proc_cpuinfo_path = proc_path / 'cpuinfo'
    proc_stat_path = proc_path / 'stat'

    # Runs once to find all the existing sensors. The sensor classes hold only
    # metadata. Values must be read in `get_cpu_stats`.
    power_telemetry_sensors = discover_power_telemetry_sensors(sys_path)

    def get_cpu_stats() -> TmpCpuStats:
        """Parse system files and get a snapshot of CPU stats.

        This function creates a snapshot of all CPU-relevant stats at the
        moment in the form of a dictionary, where keys are stat names and
        values are their values, with the exception of power consumption and CPU
        core stats. Those are structured in the same way, but each power
        telemetry sensor and each core has its own snapshot, therefore their
        snapshots are inside separate dictionaries referenced by `power_sensors`
        and `cores` keys in the snapshot.

        To illustrate:

        ```text
        cpu_stats
            load_avg_5min
            cores
                freq
                ...
            uptime
            power_sensors
                package-1
                core
                uncore
                psys
            ...
        ```

        Parses:
            - `/proc/uptime`
            - `/proc/loadavg`
            - `/proc/cpuinfo`
            - `/proc/stat`
            - `/sys/class/powercap/`
            - (NOT IMPLEMENTED) `/sys/class/hwmon/`

        Gets and calculates:
            - System uptime (in seconds)
            - CPU load average for 1, 5 and 15 min
            - CPU name (e.g. Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz)
            - Total CPU usage in per cent
            - Power consumption per each power telemetry sensor, in µW.

        Note: Whenever a file corresponding to the uptime, load average, cpu
        name or usage per cent contains an incorrect value, is not accessible
        due to a permission error or simply does not exist, the corresponding
        value is assigned `None` and a warning is issued, but the function still
        returns successfully.

        As for power telemetry sensors, it is similar, but sensors with
        incorrect or absent values are not taken into account at all.
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

        # =====================================================================
        # POWER CONSUMPTION
        # =====================================================================
        nonlocal power_telemetry_sensors
        # `None` values are for first measurements, when delta can’t be calculated.
        power_consumption_watt: dict[Path, float | None] = {}

        # TODO: Move the definition up. At the moment, the function is defined every second.
        def calculate_power_consumption():
            nonlocal power_telemetry_sensors
            nonlocal power_consumption_watt

            for s in power_telemetry_sensors.energy_sensors:
                # Because something could happen since the sensors were discovered,
                # it is important to handle possible errors here.
                try:
                    current_timestamp = time.monotonic_ns()
                    current_energy_uj_str = s.path.read_text()

                    try:
                        current_energy_uj = int(current_energy_uj_str)
                    except ValueError:
                        with warnings.catch_warnings():
                            warnings.simplefilter('default')
                            warnings.warn(
                                PowerTelemetrySensorValueWarning(
                                    current_energy_uj_str, s.path
                                )
                            )

                        # If it’s just a small glitch in the kernel/hardware, as
                        # soon as it disappears, the state starts afresh and the
                        # consumption data coming from this sensor will show correctly.
                        # DILEMMA: Might it be worth to handle the case when the
                        # glitch or whatever causes the `ValueError` does not
                        # disappear on its own? If Pytop runs for days and
                        # months, the application will waste quite a lot of
                        # resources, cumulatively, doing unnecessary work,
                        # anticipating this sensor to resume correct functioning.
                        if s.path in previous_energy:
                            print(f'Before deletion: {s}, {previous_energy}')
                            del previous_energy[s.path]
                            print(f'after deletion: {s}, {previous_energy}')

                        continue

                    if s.path not in previous_energy:
                        previous_energy[s.path] = (
                            current_energy_uj,
                            current_timestamp,
                        )
                        power_consumption_watt[s.path] = None
                        continue

                    previous_energy_uj = previous_energy[s.path][0]
                    previous_timestamp = previous_energy[s.path][1]

                    energy_delta_uj = current_energy_uj - previous_energy_uj
                    energy_delta_j = energy_delta_uj / 1_000_000
                    time_ns = current_timestamp - previous_timestamp
                    time_s = time_ns / 1_000_000_000

                    power_consumed_w = energy_delta_j / time_s
                    power_consumption_watt[s.path] = power_consumed_w

                    previous_energy[s.path] = (
                        current_energy_uj,
                        current_timestamp,
                    )
                except FileNotFoundError:
                    warnings.warn(
                        PowerTelemetrySensorNotFoundWarning(s.name, s.path)
                    )
                    break
                except PermissionError:
                    warnings.warn(
                        PowerTelemetrySensorPermissionWarning(s.name, s.path)
                    )
                    break

        with warnings.catch_warnings():
            warnings.simplefilter('error')

            try:
                calculate_power_consumption()
            except (
                PowerTelemetrySensorNotFoundWarning,
                PowerTelemetrySensorPermissionWarning,
            ) as warning:
                with warnings.catch_warnings():
                    warnings.simplefilter('default')

                    warnings.warn(warning)

                    power_telemetry_sensors = discover_power_telemetry_sensors(
                        sys_path
                    )

                    # TODO: Handle the case when this call also raises a warning.
                    calculate_power_consumption()

        return TmpCpuStats(
            name=name,
            uptime_sec=uptime_sec,
            load_avg_1min=load_avg_1min,
            load_avg_5min=load_avg_5min,
            load_avg_15min=load_avg_15min,
            usage_percent=usage_percent,
            power_consumption_watt=power_consumption_watt,
        )

    return get_cpu_stats
