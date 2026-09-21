import math
import time
from collections.abc import Callable, Generator
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
    """Return dict of paths to common dirs.

    The fixture creates a temporary directory, inserts into it `proc/` and
    `sys/class/powercap/` and returns paths to them, as well as to other common
    files and directories (without creating them) in a `CommonPaths` dataclass.
    """

    proc_path = tmp_path / 'proc'
    proc_path.mkdir()

    proc_stat = proc_path / 'stat'
    proc_cpuinfo = proc_path / 'cpuinfo'
    proc_loadavg = proc_path / 'loadavg'
    proc_uptime = proc_path / 'uptime'

    sys_path = tmp_path / 'sys'
    powercap_path = sys_path / 'class' / 'powercap'
    powercap_path.mkdir(parents=True)
    intel_rapl_path = powercap_path / 'intel-rapl'

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
        def test_is_correct(self, common_paths: CommonPaths):
            # ARRANGE
            proc_path = common_paths.proc
            proc_uptime_path = proc_path / 'uptime'
            proc_uptime_path.touch()
            proc_uptime_content = '196440.38 919502.05'
            proc_uptime_path.write_text(proc_uptime_content)
            get_cpu_stats = create_cpu_monitor(proc_path)

            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.uptime_sec == 196440.38

        class TestParsingErrors:
            class TestNoProcUptime:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANG
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ASSERT
                    with warns(ProcUptimeFileNotFoundWarning):
                        get_cpu_stats()

                def test_is_none(self, common_paths: CommonPaths):
                    """If no `/proc/uptime` found in the filesystem, then the
                    uptime must fall back to `None`."""

                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestPermissionError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def create_proc_uptime(
                    self, common_paths: CommonPaths
                ) -> Generator[None]:
                    self.proc_uptime_path = common_paths.proc / 'uptime'
                    self.proc_uptime_path.touch(0o000, False)

                    yield

                    self.proc_uptime_path = None

                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ASSERT
                    with warns(ProcUptimePermissionWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestValueError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def create_proc_uptime(
                    self, common_paths: CommonPaths
                ) -> Generator[None]:
                    self.proc_uptime_path = common_paths.proc / 'uptime'
                    self.proc_uptime_path.touch()
                    self.proc_uptime_path.write_text('incorrect content')

                    yield

                    self.proc_uptime_path = None

                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ASSERT
                    with warns(ProcUptimeValueWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

            class TestIndexError:
                proc_uptime_path: Path | None = None

                @fixture(autouse=True)
                def create_proc_uptime(
                    self, common_paths: CommonPaths
                ) -> Generator[None]:
                    self.proc_uptime_path = common_paths.proc / 'uptime'
                    self.proc_uptime_path.touch()
                    self.proc_uptime_path.write_text('')

                    yield

                    self.proc_uptime_path = None

                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ASSERT
                    with warns(ProcUptimeIndexWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.uptime_sec is None

    class TestName:
        def test_is_correct(self, common_paths: CommonPaths):
            # ARRANGE
            proc_path = common_paths.proc
            proc_cpuinfo_path = proc_path / 'cpuinfo'
            proc_cpuinfo_path.touch()
            proc_cpuinfo_content = (
                'processor\t: 0\n'
                'vendor_id\t: GenuineIntel\n'
                'cpu family\t: 6\n'
                'model\t\t: 142\n'
                'model name\t: Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz\n'
                'stepping\t: 12\n'
                'microcode\t: 0xca\n'
                'cpu MHz\t\t: 800.000\n'
                'cache size\t: 8192 KB\n'
            )
            proc_cpuinfo_path.write_text(proc_cpuinfo_content)
            get_cpu_stats = create_cpu_monitor(proc_path)

            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.name == 'Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz'

        class TestParsingErrors:
            class TestNoProcCpuinfo:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ASSERT
                    with warns(ProcCpuinfoFileNotFoundWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

            class TestPermissionError:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ASSERT
                    with warns(ProcCpuinfoPermissionWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

            class TestIndexError:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch()
                    common_paths.proc_cpuinfo.write_text('model name')
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch()
                    common_paths.proc_cpuinfo.write_text('model name')
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ASSERT
                    with warns(ProcCpuinfoIndexWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_cpuinfo.touch()
                    common_paths.proc_cpuinfo.write_text('model name')
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats.name is None

    class TestUsagePercent:
        def test_is_none_on_first_call(self, common_paths: CommonPaths):
            # ARRANGE
            proc_path = common_paths.proc
            proc_stat_path = proc_path / 'stat'
            proc_stat_path.touch()
            proc_stat_content = 'cpu\t17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content)
            get_cpu_stats = create_cpu_monitor(proc_path)

            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            assert cpu_stats.usage_percent is None

        def test_is_correct_on_second_call(self, common_paths: CommonPaths):
            """By definition, the second call happens a second later after the first
            call."""

            # ARRANGE
            proc_path = common_paths.proc
            proc_stat_path = proc_path / 'stat'
            proc_stat_path.touch()
            proc_stat_content_initial = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content_initial)
            get_cpu_stats = create_cpu_monitor(proc_path)

            # ACT
            cpu_stats_1 = get_cpu_stats()

            proc_stat_content_a_second_later = 'cpu  17080558 31047 3621744 155066266 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content_a_second_later)
            cpu_stats_2 = get_cpu_stats()

            # ASSERT
            assert cpu_stats_1.usage_percent is None
            assert cpu_stats_2.usage_percent is not None
            assert math.isclose(cpu_stats_2.usage_percent, 78)

        def test_is_correct_on_third_call(self, common_paths: CommonPaths):
            # ARRANGE
            proc_path = common_paths.proc
            proc_stat_path = proc_path / 'stat'
            proc_stat_path.touch()
            proc_stat_content_initial = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content_initial)
            get_cpu_stats = create_cpu_monitor(proc_path)

            # ACT
            cpu_stats_1 = get_cpu_stats()

            proc_stat_content_a_second_later = 'cpu  17080558 31047 3621744 155066266 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content_a_second_later)
            cpu_stats_2 = get_cpu_stats()

            proc_stat_content_another_second_later = 'cpu  17080636 31047 3621744 155066288 2810089 1482860 594878 0 0 0'
            proc_stat_path.write_text(proc_stat_content_another_second_later)
            cpu_stats_3 = get_cpu_stats()

            # ASSERT
            assert cpu_stats_1.usage_percent is None
            assert cpu_stats_2.usage_percent is not None
            assert math.isclose(cpu_stats_2.usage_percent, 78)
            assert cpu_stats_3.usage_percent is not None
            assert math.isclose(cpu_stats_3.usage_percent, 78)

        class TestParsingErrors:
            class TestNoProcStatPath:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    get_cpu_stats()
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    get_cpu_stats = create_cpu_monitor(common_paths.proc)

                    # ASSERT
                    with warns(ProcStatFileNotFoundWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats_1 = get_cpu_stats()
                    cpu_stats_2 = get_cpu_stats()
                    cpu_stats_3 = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats_1.usage_percent is None
                    assert cpu_stats_2.usage_percent is None
                    assert cpu_stats_3.usage_percent is None

            class TestPermissionError:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    get_cpu_stats()
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ASSERT
                    with warns(ProcStatPermissionWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch(0o000, False)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    cpu_stats_1 = get_cpu_stats()
                    cpu_stats_2 = get_cpu_stats()
                    cpu_stats_3 = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats_1.usage_percent is None
                    assert cpu_stats_2.usage_percent is None
                    assert cpu_stats_3.usage_percent is None

            class TestValueError:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu incorrect content'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)
                    get_cpu_stats()
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu incorrect content'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)

                    # ASSERT
                    with warns(ProcStatValueWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu incorrect content'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)
                    cpu_stats_2 = get_cpu_stats()
                    cpu_stats_3 = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats_2.usage_percent is None
                    assert cpu_stats_3.usage_percent is None

            class TestIndexError:
                def test_raises_no_error(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)
                    get_cpu_stats()
                    get_cpu_stats()

                def test_raises_warning(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)

                    # ASSERT
                    with warns(ProcStatIndexWarning):
                        get_cpu_stats()

                def test_falls_back_to_none(self, common_paths: CommonPaths):
                    # ARRANGE
                    proc_path = common_paths.proc
                    common_paths.proc_stat.touch()
                    proc_stat_content = 'cpu  17080480 31047 3621744 155066244 2810089 1482860 594878 0 0 0'
                    common_paths.proc_stat.write_text(proc_stat_content)
                    get_cpu_stats = create_cpu_monitor(proc_path)

                    # ACT
                    get_cpu_stats()
                    proc_stat_content_wrong = 'cpu'
                    common_paths.proc_stat.write_text(proc_stat_content_wrong)
                    cpu_stats_2 = get_cpu_stats()
                    cpu_stats_3 = get_cpu_stats()

                    # ASSERT
                    assert cpu_stats_2.usage_percent is None
                    assert cpu_stats_3.usage_percent is None

    class TestLoadAverage:
        load_avg_1min = 1.61
        load_avg_5min = 1.71
        load_avg_15min = 1.79
        proc_loadavg_content = (
            f'{load_avg_1min} {load_avg_5min} {load_avg_15min} 2/1455 828173'
        )

        def initialise(self, common_paths: CommonPaths):
            proc_path = common_paths.proc
            proc_loadavg_path = proc_path / 'loadavg'
            proc_loadavg_path.touch()
            proc_loadavg_path.write_text(self.proc_loadavg_content)

        @mark.parametrize(
            ['type', 'correct_value'],
            [
                ('load_avg_1min', load_avg_1min),
                ('load_avg_5min', load_avg_5min),
                ('load_avg_15min', load_avg_15min),
            ],
        )
        def test_is_correct(
            self, common_paths: CommonPaths, type: str, correct_value: float
        ):
            # ARRANGE
            self.initialise(common_paths)
            get_cpu_stats = create_cpu_monitor(common_paths.proc)

            # ACT
            cpu_stats = get_cpu_stats()

            # ASSERT
            value = getattr(cpu_stats, type)
            assert value is not None
            assert math.isclose(value, correct_value)

        class TestParsingErrors:
            class TestNoProcLoadavg:
                @mark.parametrize('type', load_avg_types)
                def test_falls_back_to_none(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

                @mark.parametrize('type', load_avg_types)
                def test_raises_no_error(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ASSERT
                    with warns(ProcLoadavgFileNotFoundWarning):
                        get_cpu_stats()

            class TestPermissionError:
                @fixture
                def get_cpu_stats(
                    self, common_paths: CommonPaths
                ) -> GetCpuStats:
                    common_paths.proc_loadvg.touch(0o000, False)
                    return create_cpu_monitor(common_paths.proc)

                @mark.parametrize('type', load_avg_types)
                def test_raises_no_error(
                    self,
                    type: str,
                    get_cpu_stats: GetCpuStats,
                    common_paths: CommonPaths,
                ):
                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self,
                    type: str,
                    get_cpu_stats: GetCpuStats,
                    common_paths: CommonPaths,
                ):
                    # ASSERT
                    with warns(ProcLoadavgPermissionWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_falls_back_to_none(
                    self,
                    type: str,
                    get_cpu_stats: GetCpuStats,
                    common_paths: CommonPaths,
                ):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

            class TestValueError:
                @fixture
                def get_cpu_stats(
                    self, common_paths: CommonPaths
                ) -> GetCpuStats:
                    common_paths.proc_loadvg.touch()
                    common_paths.proc_loadvg.write_text('incorrect content')
                    return create_cpu_monitor(common_paths.proc)

                @mark.parametrize('type', load_avg_types)
                def test_raises_no_error(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ASSERT
                    with warns(ProcLoadavgValueWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_falls_back_to_none(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

            class TestIndexError:
                @fixture
                def get_cpu_stats(
                    self, common_paths: CommonPaths
                ) -> GetCpuStats:
                    common_paths.proc_loadvg.touch()
                    common_paths.proc_loadvg.write_text('')
                    return create_cpu_monitor(common_paths.proc)

                @mark.parametrize('type', load_avg_types)
                def test_raises_no_error(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_raises_warning(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ASSERT
                    with warns(ProcLoadavgIndexWarning):
                        get_cpu_stats()

                @mark.parametrize('type', load_avg_types)
                def test_falls_back_to_none(
                    self, type: str, get_cpu_stats: GetCpuStats
                ):
                    # ACT
                    cpu_stats = get_cpu_stats()

                    # ASSERT
                    value = getattr(cpu_stats, type)
                    assert value is None

    class TestPowerConsumptionWatt:
        def test_outputs_correct_values(
            self, common_paths: CommonPaths, monkeypatch: MonkeyPatch
        ):
            # ARRANGE
            zone_path = common_paths.intel_rapl / 'intel-rapl:0'
            zone_path.mkdir(parents=True)
            sensor_path = zone_path / 'energy_uj'
            sensor_path.touch()
            sensor_path.write_text('5000000')

            get_cpu_stats = create_cpu_monitor(
                common_paths.proc, common_paths.sys
            )

            # ACT
            # This call is necessary, but the power consumption values are most
            # certainly 0 since we need Δ to calculate them in most of the
            # cases, so we aren’t interested in this snapshot.
            get_cpu_stats()

            # Now we change the output of the sensor before the next read.
            sensor_path.write_text('6000000')

            # This time, the power consumption must’ve been calculated, so we
            # take this snapshot.
            cpu_stats = get_cpu_stats()

            # ASSERT
            # The time delta is not introduced explicitly because it is simply 1
            correct_value = (6_000_000 - 5_000_000) / 1_000_000
            calculated_value = cpu_stats.power_consumption_watt[sensor_path]
            assert calculated_value is not None
            assert math.isclose(correct_value, calculated_value)

        class TestErrors:
            @mark.parametrize(
                'invalid_content', ['not-a-number', '12.5', '', '\x00\x00\x00']
            )
            def test_warns_on_value_error(
                self, common_paths: CommonPaths, invalid_content: str
            ):
                # ARRANGE
                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)
                sensor_path = zone_path / 'energy_uj'

                # The sensor must be valid during discovery.
                sensor_path.write_text('1000000')

                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # ACT
                # Corrupt the sensor file after it has been discovered.
                sensor_path.write_text(invalid_content)

                # ASSERT
                with warns(PowerTelemetrySensorValueWarning):
                    get_cpu_stats()

            def test_sensor_is_not_included_on_value_error(
                self, common_paths: CommonPaths, monkeypatch: MonkeyPatch
            ):
                # ARRANGE
                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)
                sensor_path = zone_path / 'energy_uj'
                sensor_path.write_text('1000000')

                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # ACT
                # Initial call to establish the first measurement.
                get_cpu_stats()

                # Second call with a valid delta.
                sensor_path.write_text('2000000')
                cpu_stats_1 = get_cpu_stats()

                # Third call with corrupted data.
                sensor_path.write_text('rubbish')
                with warns(PowerTelemetrySensorValueWarning):
                    cpu_stats_2 = get_cpu_stats()

                # ASSERT
                assert sensor_path in cpu_stats_1.power_consumption_watt
                assert sensor_path not in cpu_stats_2.power_consumption_watt

            def test_clears_previous_state_on_value_error(
                self, common_paths: CommonPaths, monkeypatch: MonkeyPatch
            ):
                # ARRANGE
                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)
                sensor_path = zone_path / 'energy_uj'

                # The sensor must be valid during discovery.
                sensor_path.write_text('1000000')

                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # ACT
                # Initial call to establish the first measurement.
                get_cpu_stats()

                # Second call with a valid delta.
                sensor_path.write_text('2000000')
                stats_valid = get_cpu_stats()

                # Third call with corrupted data to trigger state cleanup.
                sensor_path.write_text('rubbish')
                with warns(PowerTelemetrySensorValueWarning):
                    stats_error = get_cpu_stats()

                # 4. Fourth call with valid data to verify the state was cleared.
                sensor_path.write_text('3000000')
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

            def test_warns_if_sensor_not_found(self, common_paths: CommonPaths):
                # ARRANGE
                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)
                sensor_path = zone_path / 'energy_uj'
                sensor_path.touch()
                sensor_path.write_text('5000000')

                # ACT
                # On this call, the created sensor is discovered.
                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # Now we delete the sensor.
                sensor_path.unlink()
                assert not sensor_path.exists()

                # ASSERT
                # `get_cpu_stats()` will try to read the sensor, but there’s
                # nothing to read any longer.
                with warns(PowerTelemetrySensorNotFoundWarning):
                    get_cpu_stats()

            def test_warns_if_sensor_permission_denied(
                self, common_paths: CommonPaths
            ):
                # ARRANGE
                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)
                sensor_path = zone_path / 'energy_uj'
                sensor_path.touch()
                sensor_path.write_text('5000000')

                # ACT
                # On this call, the created sensor is discovered successfully.
                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # Now we revoke permissions before the first read in get_cpu_stats.
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
                monkeypatch: MonkeyPatch,
                recwarn: WarningsRecorder,
                warning_type: type[Warning],
                trigger_fn: Callable[[Path], object],
            ):
                # ARRANGE

                zone_path = common_paths.intel_rapl / 'intel-rapl:0'
                zone_path.mkdir(parents=True)

                sensor_path_to_fail = zone_path / 'energy_uj'
                sensor_path_to_fail.touch()
                sensor_path_to_fail.write_text('5000000', 'utf-8')

                # ACT
                # On this call, the created sensor is discovered.
                get_cpu_stats = create_cpu_monitor(
                    common_paths.proc, common_paths.sys
                )

                # Here, the sensor is still present, and its value is correct.
                cpu_stats_1 = get_cpu_stats()

                # Now, we trigger the failure on the initial sensor...
                trigger_fn(sensor_path_to_fail)

                # ...and add a new sensor.
                subzone_path = zone_path / 'intel-rapl:0:0'
                subzone_path.mkdir(parents=True)

                sensor_path_to_remain = subzone_path / 'energy_uj'
                sensor_path_to_remain.touch()
                sensor_path_to_remain.write_text('6000000', 'utf-8')
                subzone_name_path = subzone_path / 'name'
                subzone_name_path.touch()
                subzone_name_path.write_text('core', 'utf-8')

                # Since `get_cpu_stats` fails to read the initial sensor, it raises
                # a warning and starts a new sensor discovery. It discovers the
                # new sensor and reads it.
                cpu_stats_2 = get_cpu_stats()

                # Update the remaining sensor’s value.
                sensor_path_to_remain.write_text('7000000', 'utf-8')

                # Now, `get_cpu_stats()` must calculate that the power
                # consumption during the time period that passed (1 second) was 1 watt.
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

                final_sensor_power_consumption = (
                    cpu_stats_3.power_consumption_watt[sensor_path_to_remain]
                )
                assert final_sensor_power_consumption is not None
                assert math.isclose(final_sensor_power_consumption, 1)

                counter = 0
                for warning in recwarn.list:
                    if isinstance(warning.message, warning_type):
                        counter += 1
                assert counter == 1
