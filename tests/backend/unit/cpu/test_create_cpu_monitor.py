import math
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from pytest import fixture, mark, warns

from pytop.backend.cpu.create_cpu_monitor import GetCpuStats, create_cpu_monitor
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

load_avg_types = ['load_avg_1min', 'load_avg_5min', 'load_avg_15min']


@dataclass(frozen=True)
class CommonPaths:
    proc: Path
    proc_stat: Path
    proc_cpuinfo: Path
    proc_loadvg: Path
    proc_uptime: Path


@fixture
def common_paths(tmp_path: Path) -> CommonPaths:
    """Return dict of paths to common dirs.

    The fixture creates a temporary directory and inserts into it common
    directories like `proc`, relative to the temporary directory just as they
    are located relative to the root directory in a real file system.

    Illustration:

    ```text
    <tmp-dir>/
    └── proc/
    ```
    """

    proc_path = tmp_path / 'proc'
    proc_path.mkdir()

    proc_stat = proc_path / 'stat'
    proc_cpuinfo = proc_path / 'cpuinfo'
    proc_loadavg = proc_path / 'loadavg'
    proc_uptime = proc_path / 'uptime'

    return CommonPaths(
        proc_path, proc_stat, proc_cpuinfo, proc_loadavg, proc_uptime
    )


@fixture
def get_cpu_stats(common_paths: CommonPaths) -> GetCpuStats:
    return create_cpu_monitor(common_paths.proc)


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
        # TODO: Is correct.
        # ParsingErrors:
        #   TODO: No file.
        #   TODO: No permission.
        #   TODO: Wrong value.
        #   TODO: Wrong index.
        pass
