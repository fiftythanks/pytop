import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from operator import methodcaller
from pathlib import Path

from pytest import MonkeyPatch, WarningsRecorder, fixture, mark, warns

from pytop.backend.cpu.create_cpu_monitor import GetCpuStats, create_cpu_monitor
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

load_avg_types = ['load_avg_1min', 'load_avg_5min', 'load_avg_15min']


@dataclass(frozen=True)
class CommonPaths:
    proc: Path
    proc_stat: Path
    proc_cpuinfo: Path
    proc_loadvg: Path
    proc_uptime: Path
    sys: Path
    powercap: Path
    intel_rapl: Path


@fixture
def common_paths(tmp_path: Path) -> CommonPaths:
    """Return a dataclass containing paths to simulated system files.

    This fixture creates a temporary directory structure mimicking `/proc` and
    `/sys`. It populates essential files (`stat`, `cpuinfo`, `loadavg`, `uptime`,
    and `intel-rapl` energy sensors) with valid template data to ensure that
    `create_cpu_monitor` can initialize without triggering defensive warnings.
    """

    proc_path = tmp_path / 'proc'
    proc_path.mkdir()

    proc_stat = proc_path / 'stat'
    proc_stat.write_text(
        'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
        encoding='utf-8',
    )

    proc_cpuinfo = proc_path / 'cpuinfo'
    proc_cpuinfo.write_text(
        'model name\t: Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz',
        encoding='utf-8',
    )

    proc_loadavg = proc_path / 'loadavg'
    proc_loadavg.write_text('1.61 1.71 1.79 2/1455 828173', encoding='utf-8')

    proc_uptime = proc_path / 'uptime'
    proc_uptime.write_text('196440.38 919502.05', encoding='utf-8')

    sys_path = tmp_path / 'sys'
    powercap_path = sys_path / 'class' / 'powercap'
    powercap_path.mkdir(parents=True)

    hwmon_path = sys_path / 'class' / 'hwmon'
    hwmon_path.mkdir()

    intel_rapl_path = powercap_path / 'intel-rapl'
    intel_rapl_path.mkdir()

    default_zone = intel_rapl_path / 'intel-rapl:0'
    default_zone.mkdir()
    (default_zone / 'energy_uj').write_text('5000000', encoding='utf-8')
    (default_zone / 'name').write_text('package-0', encoding='utf-8')

    return CommonPaths(
        proc_path,
        proc_stat,
        proc_cpuinfo,
        proc_loadavg,
        proc_uptime,
        sys_path,
        powercap_path,
        intel_rapl_path,
    )


@fixture
def get_cpu_stats(common_paths: CommonPaths) -> GetCpuStats:
    return create_cpu_monitor(common_paths.proc, common_paths.sys)


@fixture(autouse=True)
def mock_time_monotonic_ns(monkeypatch: MonkeyPatch, step: int = 1_000_000_000):
    next_timestamp = 0

    def _mock() -> int:
        nonlocal next_timestamp
        current_timestamp = next_timestamp
        next_timestamp += step

        return current_timestamp

    monkeypatch.setattr(time, 'monotonic_ns', _mock)


class TestGetCpuData:
    """`create_cpu_monitor()` returns a function we will call `get_cpu_stats()` here."""

    class TestUptimeSec:
        def test_is_correct(self, get_cpu_stats: GetCpuStats):
            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.uptime_sec == 196440.38

        class TestParsingErrors:
            class TestNoProcUptime:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeFileNotFoundWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_uptime.unlink()

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANG
                    common_paths.proc_uptime.unlink()

                    # ASSERT
                    with warns(ProcUptimeFileNotFoundWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeFileNotFoundWarning'
                )
                def test_is_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    """If no `/proc/uptime` found in the filesystem, then the
                    uptime must fall back to `None`."""

                    # ARRANGE
                    common_paths.proc_uptime.unlink()

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestPermissionError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def restrict_proc_uptime(self, common_paths: CommonPaths):
                    common_paths.proc_uptime.chmod(0o000)

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.power_telemetry.exceptions.EnergyUjPermissionWarning',
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimePermissionWarning',
                )
                def test_raises_no_error(self, get_cpu_stats: GetCpuStats):
                    get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.power_telemetry.exceptions.EnergyUjPermissionWarning'
                )
                def test_raises_warning(self, get_cpu_stats: GetCpuStats):
                    with warns(ProcUptimePermissionWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.power_telemetry.exceptions.EnergyUjPermissionWarning',
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimePermissionWarning',
                )
                def test_falls_back_to_none(self, get_cpu_stats: GetCpuStats):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestValueError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def corrupt_proc_uptime(self, common_paths: CommonPaths):
                    common_paths.proc_uptime.write_text('incorrect content')

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeValueWarning'
                )
                def test_raises_no_error(self, get_cpu_stats: GetCpuStats):
                    get_cpu_stats()

                def test_raises_warning(self, get_cpu_stats: GetCpuStats):
                    with warns(ProcUptimeValueWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeValueWarning'
                )
                def test_falls_back_to_none(self, get_cpu_stats: GetCpuStats):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestIndexError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def empty_proc_uptime(self, common_paths: CommonPaths):
                    common_paths.proc_uptime.write_text('')

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeIndexWarning'
                )
                def test_raises_no_error(self, get_cpu_stats: GetCpuStats):
                    get_cpu_stats()

                def test_raises_warning(self, get_cpu_stats: GetCpuStats):
                    with warns(ProcUptimeIndexWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcUptimeIndexWarning'
                )
                def test_falls_back_to_none(self, get_cpu_stats: GetCpuStats):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

    class TestName:
        def test_is_correct(self, get_cpu_stats: GetCpuStats):
            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.name == 'Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz'

        class TestParsingErrors:
            class TestNoProcCpuinfo:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoFileNotFoundWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.unlink()

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.unlink()

                    # ASSERT
                    with warns(ProcCpuinfoFileNotFoundWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoFileNotFoundWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.unlink()

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

            class TestPermissionError:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoPermissionWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.chmod(0o000)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.chmod(0o000)

                    # ASSERT
                    with warns(ProcCpuinfoPermissionWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoPermissionWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.chmod(0o000)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

            class TestIndexError:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoIndexWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.write_text('model name')

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.write_text('model name')

                    # ASSERT
                    with warns(ProcCpuinfoIndexWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcCpuinfoIndexWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_cpuinfo.write_text('model name')

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

    class TestUsagePercent:
        def test_is_none_on_first_call(self, get_cpu_stats: GetCpuStats):
            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.usage_percent is None

        def test_is_correct_on_second_call(
            self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
        ):
            # ACT
            get_cpu_stats()
            common_paths.proc_stat.write_text(
                'cpu  17080558 31047 3621744 155066266 2810089 1482860 594878 0 0 0'
            )
            cpu_stats_2 = get_cpu_stats()

            # ASSERT
            assert cpu_stats_2.usage_percent is not None
            assert math.isclose(cpu_stats_2.usage_percent, 78)

        def test_is_correct_on_third_call(
            self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
        ):
            # ACT
            get_cpu_stats()
            common_paths.proc_stat.write_text(
                'cpu  17080558 31047 3621744 155066266 2810089 1482860 594878 0 0 0'
            )
            get_cpu_stats()
            common_paths.proc_stat.write_text(
                'cpu  17080636 31047 3621744 155066288 2810089 1482860 594878 0 0 0'
            )
            cpu_stats_3 = get_cpu_stats()

            # ASSERT
            assert cpu_stats_3.usage_percent is not None
            assert math.isclose(cpu_stats_3.usage_percent, 78)

        class TestParsingErrors:
            class TestNoProcStatPath:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatFileNotFoundWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.unlink()

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.unlink()

                    # ASSERT
                    with warns(ProcStatFileNotFoundWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatFileNotFoundWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.unlink()

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.usage_percent is None

            class TestPermissionError:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatPermissionWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.chmod(0o000)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.chmod(0o000)

                    # ASSERT
                    with warns(ProcStatPermissionWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatPermissionWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ARRANGE
                    common_paths.proc_stat.chmod(0o000)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.usage_percent is None

            class TestValueError:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatValueWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu incorrect content')
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu incorrect content')

                    # ASSERT
                    with warns(ProcStatValueWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatValueWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu incorrect content')
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.usage_percent is None

            class TestIndexError:
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatIndexWarning'
                )
                def test_raises_no_error(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu')
                    get_cpu_stats()

                def test_raises_warning(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu')

                    # ASSERT
                    with warns(ProcStatIndexWarning):
                        get_cpu_stats()

                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcStatIndexWarning'
                )
                def test_falls_back_to_none(
                    self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()
                    common_paths.proc_stat.write_text('cpu')
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.usage_percent is None

    class TestLoadAverage:
        @mark.parametrize(
            ['type', 'correct_value'],
            [
                ('load_avg_1min', 1.61),
                ('load_avg_5min', 1.71),
                ('load_avg_15min', 1.79),
            ],
        )
        def test_is_correct(
            self, get_cpu_stats: GetCpuStats, type: str, correct_value: float
        ):
            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            value = getattr(cpu_stats, type)
            assert value is not None
            assert math.isclose(value, correct_value)

        class TestParsingErrors:
            class TestNoProcLoadavg:
                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgFileNotFoundWarning'
                )
                def test_falls_back_to_none(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.unlink()

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgFileNotFoundWarning'
                )
                def test_raises_no_error(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.unlink()

                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.unlink()

                    # ASSERT
                    with warns(ProcLoadavgFileNotFoundWarning):
                        get_cpu_stats()

            class TestPermissionError:
                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgPermissionWarning'
                )
                def test_raises_no_error(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.chmod(0o000)

                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.chmod(0o000)

                    # ASSERT
                    with warns(ProcLoadavgPermissionWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgPermissionWarning'
                )
                def test_falls_back_to_none(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.chmod(0o000)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

            class TestValueError:
                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgValueWarning'
                )
                def test_raises_no_error(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('incorrect content')

                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('incorrect content')

                    # ASSERT
                    with warns(ProcLoadavgValueWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgValueWarning'
                )
                def test_falls_back_to_none(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('incorrect content')

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

            class TestIndexError:
                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgIndexWarning'
                )
                def test_raises_no_error(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('')

                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('')

                    # ASSERT
                    with warns(ProcLoadavgIndexWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                @mark.filterwarnings(
                    'ignore::pytop.backend.cpu.exceptions.ProcLoadavgIndexWarning'
                )
                def test_falls_back_to_none(
                    self,
                    type: str,
                    common_paths: CommonPaths,
                    get_cpu_stats: GetCpuStats,
                ):
                    # ARRANGE
                    common_paths.proc_loadvg.write_text('')

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

    class TestPowerConsumptionWatt:
        def test_outputs_correct_values(
            self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
        ):
            # ARRANGE
            sensor_path = common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'

            # ACT
            get_cpu_stats()

            # Now we change the output of the sensor before the next read.
            sensor_path.write_text('6000000')

            # And, just to ensure we don’t get a division-by-zero error, we
            # increase system tick count.
            common_paths.proc_stat.write_text(
                'cpu  18080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                encoding='utf-8',
            )

            cpu_stats = get_cpu_stats()

            # ASSERT
            correct_value = (6_000_000 - 5_000_000) / 1_000_000
            calculated_value = cpu_stats.power_consumption_watt[sensor_path]
            assert calculated_value is not None
            assert math.isclose(correct_value, calculated_value)

        class TestErrors:
            @mark.parametrize(
                'invalid_content', ['not-a-number', '12.5', '', '\x00\x00\x00']
            )
            def test_warns_on_value_error(
                self,
                common_paths: CommonPaths,
                get_cpu_stats: GetCpuStats,
                invalid_content: str,
            ):
                # ARRANGE
                sensor_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                sensor_path.write_text(invalid_content)

                # ASSERT
                with warns(PowerTelemetrySensorValueWarning):
                    get_cpu_stats()

            @mark.filterwarnings(
                'ignore::pytop.backend.cpu.exceptions.PowerTelemetrySensorValueWarning'
            )
            def test_sensor_is_not_included_on_value_error(
                self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
            ):
                # ARRANGE
                sensor_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                get_cpu_stats()

                # Second call with a valid delta.
                common_paths.proc_stat.write_text(
                    'cpu  18080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )
                sensor_path.write_text('6000000')
                cpu_stats_1 = get_cpu_stats()

                # Third call with corrupted data.
                common_paths.proc_stat.write_text(
                    'cpu  18100479 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )
                sensor_path.write_text('rubbish')
                cpu_stats_2 = get_cpu_stats()

                # ASSERT
                assert sensor_path in cpu_stats_1.power_consumption_watt
                assert sensor_path not in cpu_stats_2.power_consumption_watt

            @mark.filterwarnings(
                'ignore::pytop.backend.cpu.exceptions.PowerTelemetrySensorValueWarning'
            )
            def test_clears_previous_state_on_value_error(
                self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
            ):
                # ARRANGE
                sensor_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                get_cpu_stats()

                # Second call with a valid delta.
                common_paths.proc_stat.write_text(
                    'cpu  18080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )
                sensor_path.write_text('6000000')
                stats_valid = get_cpu_stats()

                # Third call with corrupted data to trigger state cleanup.
                common_paths.proc_stat.write_text(
                    'cpu  18090479 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )
                sensor_path.write_text('rubbish')
                stats_error = get_cpu_stats()

                # 4. Fourth call with valid data to verify the state was cleared.
                common_paths.proc_stat.write_text(
                    'cpu  18080579 41046 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )
                sensor_path.write_text('7000000')
                stats_recovered = get_cpu_stats()

                # ASSERT
                calculated_power = stats_valid.power_consumption_watt[
                    sensor_path
                ]
                assert calculated_power is not None
                assert math.isclose(calculated_power, 1.0)

                assert sensor_path not in stats_error.power_consumption_watt

                # Since the state was cleared in the previous step, this call
                # should treat the sensor as a fresh first measurement.
                assert sensor_path in stats_recovered.power_consumption_watt
                assert (
                    stats_recovered.power_consumption_watt[sensor_path] is None
                )

            @mark.filterwarnings(
                'ignore::pytop.backend.cpu.power_telemetry.exceptions.EnergyUjNotFoundWarning'
            )
            def test_warns_if_sensor_not_found(
                self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
            ):
                # ARRANGE
                sensor_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                sensor_path.unlink()

                # ASSERT
                with warns(PowerTelemetrySensorNotFoundWarning):
                    get_cpu_stats()

            @mark.filterwarnings(
                'ignore::pytop.backend.cpu.power_telemetry.exceptions.EnergyUjPermissionWarning'
            )
            def test_warns_if_sensor_permission_denied(
                self, common_paths: CommonPaths, get_cpu_stats: GetCpuStats
            ):
                # ARRANGE
                sensor_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                sensor_path.chmod(0o000)

                # ASSERT
                with warns(PowerTelemetrySensorPermissionWarning):
                    get_cpu_stats()

            @mark.parametrize(
                ['warning_type', 'trigger_fn'],
                [
                    (
                        PowerTelemetrySensorNotFoundWarning,
                        methodcaller('unlink'),
                    ),
                    (
                        PowerTelemetrySensorPermissionWarning,
                        methodcaller('chmod', 0o000),
                    ),
                ],
            )
            def test_rediscovers_sensors_and_gives_correct_stats(
                self,
                common_paths: CommonPaths,
                get_cpu_stats: GetCpuStats,
                recwarn: WarningsRecorder,
                warning_type: type[Warning],
                trigger_fn: Callable[[Path], object],
            ):
                # ARRANGE
                sensor_path_to_fail = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'energy_uj'
                )

                # ACT
                cpu_stats_1 = get_cpu_stats()

                # Trigger failure
                trigger_fn(sensor_path_to_fail)

                # Add new sensor
                subzone_path = (
                    common_paths.intel_rapl / 'intel-rapl:0' / 'intel-rapl:0:0'
                )
                subzone_path.mkdir(parents=True)
                sensor_path_to_remain = subzone_path / 'energy_uj'
                sensor_path_to_remain.write_text('6000000', 'utf-8')
                (subzone_path / 'name').write_text('core', 'utf-8')

                common_paths.proc_stat.write_text(
                    'cpu  18080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )

                # Discovery happens on failure
                cpu_stats_2 = get_cpu_stats()

                common_paths.proc_stat.write_text(
                    'cpu  18081479 31047 3621744 155066244 2810089 1482860 594878 0 0 0',
                    encoding='utf-8',
                )

                # Update value
                sensor_path_to_remain.write_text('7000000', 'utf-8')
                cpu_stats_3 = get_cpu_stats()

                # ASSERT
                assert sensor_path_to_fail in cpu_stats_1.power_consumption_watt
                assert (
                    sensor_path_to_fail
                    not in cpu_stats_2.power_consumption_watt
                    and sensor_path_to_fail
                    not in cpu_stats_3.power_consumption_watt
                )
                assert (
                    sensor_path_to_remain in cpu_stats_2.power_consumption_watt
                    and sensor_path_to_remain
                    in cpu_stats_3.power_consumption_watt
                )

                final_power = cpu_stats_3.power_consumption_watt[
                    sensor_path_to_remain
                ]
                assert final_power is not None
                assert math.isclose(final_power, 1.0)

                assert any(
                    isinstance(w.message, warning_type) for w in recwarn.list
                )
