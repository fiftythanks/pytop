from typing import ClassVar, Literal

import pytest
from pytest import Subtests

from pytop.backend.proc.create_process_monitor import create_process_monitor
from tests.backend.unit.proc.conftest import ProcHelpers


class TestCreateProcessMonitor:
    class TestGetProcesses:
        def test_includes_all_processes(self, proc_helpers: ProcHelpers):
            """`get_processes()` must parse all and only PID-named subdirectories in the
            given directory."""

            # ARRANGE
            get_processes = create_process_monitor(proc_helpers['dir'])

            # ACT
            processes = get_processes()
            process_pids = list(processes.keys())
            process_pids.sort()

            # ASSERT
            assert list(proc_helpers['expected_pids']) == process_pids

        class TestStatus:
            Fallback = type[int] | None
            Field = Literal[
                'pid',
                'name',
                'ppid',
                'threads',
                'vmrss',
                'state',
                'effective_user_name',
            ]
            field_defaults: ClassVar[dict[Field, Fallback]] = {
                'pid': int,
                'name': None,
                'ppid': None,
                'threads': None,
                'vmrss': None,
                'state': None,
                'effective_user_name': None,
            }

            def test_is_absent(self, proc_helpers: ProcHelpers):
                """`get_processes()` should not include into the resulting list processes which do not have `status` files."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pid = proc_helpers['status_absent']

                # ASSERT
                assert target_pid not in processes

            def test_cannot_read(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """`get_processes()` must include the processes whose `status` Pytop has no read access to."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers['status_no_read']

                # ASSERT
                for pid in target_pids:
                    with subtests.test(
                        '`processes` lacks relevant PID', pid=pid
                    ):
                        assert pid in processes

            def test_is_empty(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """`get_processes()` must include into the resulting list processes whose `status` files are empty."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers['status_empty']

                # ASSERT
                for pid in target_pids:
                    with subtests.test(
                        '`processes` lacks relevant PID', pid=pid
                    ):
                        assert pid in processes

            @pytest.mark.parametrize('field, fallback', field_defaults.items())
            def test_fallbacks(
                self,
                proc_helpers: ProcHelpers,
                field: Field,
                fallback: Fallback,
                subtests: Subtests,
            ):
                """`get_processes()` must provide each field with a correct fallback value if `/proc/<status>/status` can’t be read or is empty."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = {
                    *proc_helpers['status_no_read'],
                    *proc_helpers['status_empty'],
                }

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Wrong fallback', pid=pid, field=field):
                        value = getattr(processes[pid], field)

                        if fallback is None:
                            assert value is None
                        else:
                            # If `fallback is not None`, the `field` is `pid`.
                            assert value == pid

            def test_name_with_spaces_and_tabs(self, proc_helpers: ProcHelpers):
                """`get_processes()` must preserve spaces and tabs in the name from `status`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pid = proc_helpers['status_name_spaces_and_tabs']

                # ASSERT
                assert (
                    processes[target_pid].name
                    == proc_helpers['name_with_spaces_and_tabs']
                )

            def test_ppid_has_non_numbers(self, proc_helpers: ProcHelpers):
                """If the PPid field in `status` contains non-numeric non-space symbols, `process.ppid` should fallback to `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_process = processes[proc_helpers['non_numeric_ppid']]

                # ASSERT
                assert target_process.ppid is None

            def test_only_first_number_in_ppid_is_parsed(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """Only the first number in "PPid" should be taken into account. Anything else should not be parsed."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers['pids_of_multiple_number_ppid_proc']

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Incorrect PPid', pid=pid):
                        assert processes[pid].ppid == int(
                            proc_helpers[
                                'ppid_of_multiple_numbers_space'
                            ].split(' ', 1)[0]
                        ) or processes[pid].ppid == int(
                            proc_helpers['ppid_of_multiple_numbers_tab'].split(
                                '\t', 1
                            )[0]
                        )

            def test_threads_is_not_number(self, proc_helpers: ProcHelpers):
                """`threads` should fallback to `None` if the "Threads" field in `status` is not a number and not a set of symbol sequences separated by spaces or tabs where the first sequence is a number."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_process = processes[proc_helpers['wrong_threads_value']]

                # ASSERT
                assert target_process.threads is None

            def test_only_first_number_in_threads_is_parsed(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """Only the first number in "Threads" should be taken. Everything else should not be parsed."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers[
                    'pids_of_multiple_number_threads_proc'
                ]

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Incorrect threads value', pid=pid):
                        assert processes[pid].threads == int(
                            proc_helpers[
                                'threads_of_multiple_numbers_space'
                            ].split(' ', 1)[0]
                        ) or processes[pid].threads == int(
                            proc_helpers[
                                'threads_of_multiple_numbers_tab'
                            ].split('\t', 1)[0]
                        )

            @pytest.mark.parametrize(
                'field, pids_tuple',
                [
                    ('uid', 'wrong_uid'),
                    ('vmrss', 'wrong_vmrss'),
                    ('state', 'wrong_state'),
                ],
            )
            def test_wrong_format(
                self,
                proc_helpers: ProcHelpers,
                field: Literal['uid', 'vmrss', 'state'],
                pids_tuple: Literal['wrong_uid', 'wrong_vmrss', 'wrong_state'],
                subtests: Subtests,
            ):
                """When the “Uid”, “VmRSS” or “State” field has a wrong value in `status`, `effective_user_name`, `vmrss` and `state`, respectively, must fallback to `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers[pids_tuple]

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Wrong fallback', pid=pid):
                        if field == 'uid':
                            assert processes[pid].effective_user_name is None
                        else:
                            assert getattr(processes[pid], field) is None

            @pytest.mark.parametrize(
                'field', ['Name', 'PPid', 'Threads', 'Uid', 'VmRSS', 'State']
            )
            def test_empty_field(
                self,
                proc_helpers: ProcHelpers,
                field: Literal[
                    'Name', 'PPid', 'Threads', 'Uid', 'VmRSS', 'State'
                ],
            ):
                """If `status` contains a field, but it has no value, the corresponding attribute must be `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])
                pid = 99

                generate_process = proc_helpers['generate_process']
                generate_process(pid=pid, status=f'{field}:\t')

                # ACT
                processes = get_processes()

                key = ''
                if field == 'Uid':
                    key = 'effective_user_name'
                else:
                    key = field.lower()

                # ASSERT
                assert getattr(processes[pid], key) is None

            def test_no_user_with_uid(self, proc_helpers: ProcHelpers):
                """If the effective UID taken from the UID provided by `status` points to no existing user, `effective_user_name` must take the EUID as its value."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                pid = 999
                euid = 9998999

                generate_process = proc_helpers['generate_process']
                ruid = 9999999
                ssuid = 9998799
                fsuid = 9349299
                status = f'Pid:\t999\nUid:\t{ruid}\t{euid}\t{ssuid}\t{fsuid}'
                generate_process(pid=pid, status=status)

                # ACT
                processes = get_processes()
                target_process = processes[pid]

                # ASSERT
                assert target_process.effective_user_name == str(euid)

        class TestIo:
            def test_cannot_read(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """`get_processes()` must include into the resulting list the processes whose `io` Pytop has no read access to."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                for pid in proc_helpers['io_no_read']:
                    with subtests.test(
                        'Process missing from the result', pid=pid
                    ):
                        assert pid in processes

            def test_io_absent(self, proc_helpers: ProcHelpers):
                """`get_processes()` must include into the resulting list the processes that don’t have `io` files."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                assert proc_helpers['io_absent'] in processes

            @pytest.mark.parametrize('field', ['read_bytes', 'write_bytes'])
            def test_fallbacks(
                self,
                proc_helpers: ProcHelpers,
                field: Literal['read_bytes', 'write_bytes'],
                subtests: Subtests,
            ):
                """When `io` is either absent or Pytop can’t read it, `read_bytes` and `write_bytes` should default to `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = {
                    *proc_helpers['io_no_read'],
                    proc_helpers['io_absent'],
                }

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Wrong fallback', pid=pid, field=field):
                        assert getattr(processes[pid], field) is None

            @pytest.mark.parametrize(
                'field, pids',
                [
                    ('read_bytes', 'wrong_read_bytes'),
                    ('write_bytes', 'wrong_write_bytes'),
                ],
            )
            def test_wrong_format(
                self,
                proc_helpers: ProcHelpers,
                subtests: Subtests,
                field: Literal['read_bytes', 'write_bytes'],
                pids: Literal['wrong_read_bytes', 'wrong_write_bytes'],
            ):
                """If “read_bytes” or “write_bytes” in `io` are in a wrong format and their values aren’t separated by spaces or tabs in such a way that the first subvalue is a number that would be the correct value if it would be used alone, then the corresponding attributes of the corresponding process should fallback to `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()
                target_pids = proc_helpers[pids]

                # ASSERT
                for pid in target_pids:
                    with subtests.test('Wrong fallback', pid=pid):
                        assert getattr(processes[pid], field) is None

            # TODO: Refactor a bit to make the test more logical. Precisely, you have
            # tuples of PIDs, but compare to one value in the assertions.
            @pytest.mark.parametrize(
                'field, sep, pids, wrong_value',
                [
                    (
                        'read_bytes',
                        'space',
                        'pids_of_multiple_number_read_bytes_proc_space',
                        'read_bytes_of_multiple_numbers_space',
                    ),
                    (
                        'read_bytes',
                        'tab',
                        'pids_of_multiple_number_read_bytes_proc_tab',
                        'read_bytes_of_multiple_numbers_tab',
                    ),
                    (
                        'write_bytes',
                        'space',
                        'pids_of_multiple_number_write_bytes_proc_space',
                        'write_bytes_of_multiple_numbers_space',
                    ),
                    (
                        'write_bytes',
                        'tab',
                        'pids_of_multiple_number_write_bytes_proc_tab',
                        'write_bytes_of_multiple_numbers_tab',
                    ),
                ],
            )
            def test_only_first_number_is_parsed(
                self,
                proc_helpers: ProcHelpers,
                subtests: Subtests,
                field: Literal['read_bytes', 'write_bytes'],
                sep: Literal['space', 'tab'],
                pids: Literal[
                    'pids_of_multiple_number_read_bytes_proc_space',
                    'pids_of_multiple_number_read_bytes_proc_tab',
                    'pids_of_multiple_number_write_bytes_proc_space',
                    'pids_of_multiple_number_write_bytes_proc_tab',
                ],
                wrong_value: Literal[
                    'read_bytes_of_multiple_numbers_space',
                    'read_bytes_of_multiple_numbers_tab',
                    'write_bytes_of_multiple_numbers_space',
                    'write_bytes_of_multiple_numbers_tab',
                ],
            ):
                """Only the first number in `read_bytes`/`write_bytes` should be taken. Everything else should not be parsed."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                target_pids = proc_helpers[pids]
                for pid in target_pids:
                    with subtests.test(
                        'Wrong value', pid=pid, field=field, sep=sep
                    ):
                        process = processes[pid]
                        target_value = getattr(process, field)
                        correct_fallback = int(
                            proc_helpers[wrong_value].split()[0]
                        )
                        assert target_value == correct_fallback

        class TestCmdline:
            def test_cannot_read(self, proc_helpers: ProcHelpers):
                """`get_processes()` must include into the resulting list the processes whose `cmdline` files it doesn’t have read access to."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                assert proc_helpers['cmdline_no_read'] in processes

            def test_is_absent(self, proc_helpers: ProcHelpers):
                """`get_processes()` must include into the resulting list the processes whose `cmdline` file don’t exist."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                assert proc_helpers['cmdline_absent'] in processes

            def test_fallbacks(
                self, proc_helpers: ProcHelpers, subtests: Subtests
            ):
                """When `cmdline` is either absent or Pytop can’t read it, `cmd` should default to `None`."""

                # ARRANGE
                get_processes = create_process_monitor(proc_helpers['dir'])

                # ACT
                processes = get_processes()

                # ASSERT
                for pid in {
                    proc_helpers['cmdline_no_read'],
                    proc_helpers['cmdline_absent'],
                }:
                    with subtests.test('Wrong default', pid=pid):
                        assert processes[pid].cmd is None

        class TestUptime:
            def test_measured_correctly(self, proc_helpers: ProcHelpers):
                # ARRANGE
                generate_process = proc_helpers['generate_process']
                get_processes = create_process_monitor(proc_helpers['dir'])
                target_pid = 8532

                # One second after the first read.
                proc_uptime_content = '468285.83 936571.66'

                proc_pid_stat_content = '8532 (pytop) R 1204 8532 8532 34816 8532 4194304 345 0 0 0 1330 370 0 0 20 0 1 0 46820000 18857984 2200 18446744073709551615 940000000000 940000050000 140737488340000 0 0 0 0 0 0 0 0 17 1 0 0 15 0 0 940000060000 940000080000 940000100000 140737488350000 140737488350100 140737488350100 140737488350500 0'
                generate_process(pid=target_pid, status=proc_pid_stat_content)

                # ACT
                processes_initial = get_processes()

                # Change `/proc/uptime` so as if 1 second passed
                proc_uptime_file = proc_helpers['dir'] / 'uptime'
                proc_uptime_file.write_text(proc_uptime_content, 'utf-8')

                # After 1 second
                processes_final = get_processes()

                # ASSERT
                uptime_initial = processes_initial[target_pid].uptime_ms
                uptime_final = processes_final[target_pid].uptime_ms
                assert uptime_initial is not None and uptime_final is not None
                assert uptime_final - uptime_initial == 1_000

            def test_does_not_break_when_pname_has_spaces(
                self, proc_helpers: ProcHelpers
            ):
                # ARRANGE
                generate_process = proc_helpers['generate_process']
                get_processes = create_process_monitor(proc_helpers['dir'])
                target_pid = 8532
                pname = 'some name With\t spaces and tab)s and all() kinds of symbols))))'

                # One second after the first read.
                proc_uptime_content = '468285.83 936571.66'

                proc_pid_stat_content = f'8532 ({pname}) R 1204 8532 8532 34816 8532 4194304 345 0 0 0 1330 370 0 0 20 0 1 0 46820000 18857984 2200 18446744073709551615 940000000000 940000050000 140737488340000 0 0 0 0 0 0 0 0 17 1 0 0 15 0 0 940000060000 940000080000 940000100000 140737488350000 140737488350100 140737488350100 140737488350500 0'
                generate_process(pid=target_pid, status=proc_pid_stat_content)

                # ACT
                processes_initial = get_processes()

                # Change `/proc/uptime` so as if 1 second passed
                proc_uptime_file = proc_helpers['dir'] / 'uptime'
                proc_uptime_file.write_text(proc_uptime_content, 'utf-8')

                # After 1 second
                processes_final = get_processes()

                # ASSERT
                uptime_initial = processes_initial[target_pid].uptime_ms
                uptime_final = processes_final[target_pid].uptime_ms
                assert uptime_initial is not None and uptime_final is not None
                assert uptime_final - uptime_initial == 1_000

        class TestCpuUsage:
            def test_measured_correctly(self, proc_helpers: ProcHelpers):
                # ARRANGE
                generate_process = proc_helpers['generate_process']
                get_processes = create_process_monitor(proc_helpers['dir'])
                target_pid = 86031

                initial_proc_pid_stat_content = '86031 (pytop) S 1 86031 86031 0 -1 4194304 1200 0 0 0 150 50 0 0 20 0 4 0 36828483 52428800 1200 18446744073709551615 1 1 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0'

                final_proc_pid_stat_content = '86031 (pytop) R 1 86031 86031 0 -1 4194304 1220 0 0 0 158 52 0 0 20 0 4 0 36828483 52428800 1200 18446744073709551615 1 1 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0'

                final_proc_stat_content = """\
                cpu 10132163 290696 3084729 46828663 16683 0 25195 0 175628 0
                cpu0 5066081 145348 1542364 23414331 8341 0 12597 0 87814 0
                cpu1 5066082 145348 1542365 23414332 8342 0 12598 0 87814 0
                page 5741 1808
                swap 1 0
                intr 1462898 1204 0 0 15 0 0 0 0 0 0 0 0 452 0 0
                disk_io: (2,0):(31,30,5764,1,2)
                ctxt 115465
                btime 1700000000
                processes 86036
                procs_running 2
                procs_blocked 0
                softirq 229245889 94 60001584 13619 5175704 2471304 28 51212741 59130143 0 51240672
                """

                final_proc_uptime_content = '468285.83 936571.46'

                generate_process(
                    pid=target_pid,
                    status='Name:\tpytop\n',
                    stat=initial_proc_pid_stat_content,
                )

                # ACT
                # Initial measurement
                initial_processes = get_processes()
                print(f'Initial process: {initial_processes[target_pid]}')

                # Simulate 1 second pass and 5% per core usage by PID 86031
                proc_dir = proc_helpers['dir']

                proc_pid_stat_file = proc_dir / str(target_pid) / 'stat'
                proc_pid_stat_file.write_text(
                    final_proc_pid_stat_content, 'utf-8'
                )

                proc_stat_file = proc_dir / 'stat'
                proc_stat_file.write_text(final_proc_stat_content, 'utf-8')

                proc_uptime_file = proc_dir / 'uptime'
                proc_uptime_file.write_text(final_proc_uptime_content, 'utf-8')

                # Measurement after 1 second
                final_processes = get_processes()
                print(f'Final process: {final_processes[target_pid]}')

                # ASSERT
                assert final_processes[target_pid].cpu_usage_percent == 10
