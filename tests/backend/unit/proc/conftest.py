import os
from collections.abc import Generator
from pathlib import Path
from typing import Literal, Protocol, TypedDict

import pytest

ExpectedPids = tuple[
    Literal[1],
    Literal[2],
    Literal[3],
    Literal[4],
    Literal[5],
    Literal[6],
    Literal[7],
    Literal[8],
    Literal[9],
    Literal[10],
    Literal[11],
    Literal[12],
    Literal[13],
    Literal[14],
    Literal[15],
    Literal[16],
    Literal[17],
    Literal[18],
    Literal[20],
    Literal[21],
    Literal[22],
    Literal[23],
    Literal[24],
    Literal[25],
    Literal[26],
    Literal[27],
]


class GenerateProcess(Protocol):
    def __call__(
        self,
        pid: int,
        status: str | None = None,
        io: str | None = None,
        cmdline: str | None = None,
        stat: str | None = None,
        status_mode: int = 0o666,
        io_mode: int = 0o666,
        cmdline_mode: int = 0o666,
        stat_mode: int = 0o666,
    ) -> None: ...


class ProcHelpers(TypedDict):
    dir: Path
    expected_pids: ExpectedPids
    io_no_read: tuple[Literal[2]]
    status_no_read: tuple[Literal[4]]
    status_empty: tuple[Literal[5]]
    status_name_spaces_and_tabs: Literal[6]
    name_with_spaces_and_tabs: str
    io_absent: Literal[7]
    cmdline_no_read: Literal[8]
    cmdline_absent: Literal[9]
    non_numeric_ppid: Literal[10]
    pids_of_multiple_number_ppid_proc: tuple[Literal[11], Literal[12]]
    ppid_of_multiple_numbers_space: str
    ppid_of_multiple_numbers_tab: str
    wrong_threads_value: Literal[13]
    pids_of_multiple_number_threads_proc: tuple[Literal[14], Literal[15]]
    threads_of_multiple_numbers_space: str
    threads_of_multiple_numbers_tab: str
    wrong_uid: tuple[Literal[16]]
    wrong_vmrss: tuple[Literal[17]]
    wrong_state: tuple[Literal[18]]
    status_absent: Literal[19]
    wrong_read_bytes: tuple[Literal[20], Literal[26]]
    wrong_write_bytes: tuple[Literal[21], Literal[27]]
    pids_of_multiple_number_read_bytes_proc_space: tuple[Literal[22]]
    pids_of_multiple_number_read_bytes_proc_tab: tuple[Literal[23]]
    pids_of_multiple_number_write_bytes_proc_space: tuple[Literal[24]]
    pids_of_multiple_number_write_bytes_proc_tab: tuple[Literal[25]]
    read_bytes_of_multiple_numbers_space: str
    read_bytes_of_multiple_numbers_tab: str
    write_bytes_of_multiple_numbers_space: str
    write_bytes_of_multiple_numbers_tab: str
    read_bytes_empty: Literal[26]
    write_bytes_empty: Literal[27]
    generate_process: GenerateProcess


@pytest.fixture
def proc_helpers(tmp_path: Path) -> ProcHelpers:
    """Constructs a `/proc/`-like directory with processes statically and returns a function for generating more processes and putting into the directory dynamically.

    Process IDs and descriptions:
    - PID 1: Each file is accessible to Pytop, contains expected content, isn’t empty.
    - PID 2: `status`, `cmdline` are accessible; `io` isn’t accessible to Pytop; each file contains expected content; `status` and `io` aren’t empty; `cmdline` is empty.
    - PID 3: Each file is accessible to Pytop, contains expected content, isn’t empty; `cmdline` contains a command with flags.
    - PID 4: `io`, `cmdline` are accessible; `status` isn’t accessible to Pytop; each file contains expected content; `status` and `io` aren’t empty; `cmdline` is empty.
    - PID 5: Each file is accessible to Pytop, `io` and `cmdline` contain expected content, `status` and `cmdline` are empty.
    - PID 6: Each file is accessible to Pytop, contains expected content, isn’t empty; the value of the field `name` in `status` contains spaces and tabs.
    - PID 7: `io` is absent, the rest of the files are accessible to Pytop, contain expected content, aren’t empty.
    - PID 8: `status`, `io` are accessible, `cmdline` isn’t accessible to Pytop; each file contains expected content and isn’t empty.
    - PID 9: `cmdline` doesn’t exist; the rest of the files are accessible to Pytop, contain expected content and aren’t empty.
    - PID 10: Each file is accessible to Pytop; `status` contains “PPid” that has non-numeric symbols in it, `io` and `cmdline` contain expected content; no file is empty.
    - PID 11: Each file is accessible to Pytop; `status` contains “PPid” that consists of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a space; `io` and `cmdline` contain expected content; no file is empty.
    - PID 12: Each file is accessible to Pytop; `status` contains “PPid” that consists of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a tab; `io` and `cmdline` contain expected content; no file is empty.
    - PID 13: Each file is accessible to Pytop; `status` contains “Threads” that has non-numeric symbols in it, `io` and `cmdline` contain expected content; no file is empty.
    - PID 14: Each file is accessible to Pytop; `status` contains “Threads” that consists of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a space; `io` and `cmdline` contain expected content; no file is empty.
    - PID 15: Each file is accessible to Pytop; `status` contains “Threads” that consists of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a tab; `io` and `cmdline` contain expected content; no file is empty.
    - PID 16: Each file is accessible to Pytop, `status` has “Uid” in a wrong format, everything else is correct and non-empty.
    - PID 17: Each file is accessible to Pytop, `status` has “VmRSS” in a wrong format, everything else is correct and non-empty.
    - PID 18: Each file is accessible to Pytop, `status` has “State” in a wrong format, everything else is correct and non-empty.
    - PID 19: `status` is absent, everything else is as expected.
    - PID 20: `read_bytes` in `io` is completely wrong, everything else is as expected.
    - PID 21: `write_bytes` in `io` is completely wrong, everything else is as expected.
    - PID 22: `read_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a space from everything else.
    - PID 23: `read_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a tab from everything else.
    - PID 24: `write_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a space from everything else.
    - PID 25: `write_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a tab from everything else.
    - PID 26: `read_bytes` in `io` is empty.
    - PID 27: `write_bytes` in `io` is empty.

    Returns:
        dict:
            'dir': The constructed directory’s `Path`
            'expected_pids': A tuple of PIDs of processes the test must expect to be in the directory
            'io_no_read': A tuple of PIDs of processes whose `io` files aren’t accessible to Pytop
            'status_no_read': A tuple of PIDs of processes whose `status` files aren’t accessible to Pytop
            'status_empty': A tuple of PIDs of processes whose `status` files are empty.
            'status_name_spaces_and_tabs': The PID of the process whose name contains spaces and tabs.
            'name_with_spaces_and_tabs': The name with spaces and tabs mentioned above.
            'io_absent': The PID of the process that doesn’t have an `io` file.
            'cmdline_no_read': The PID of the process whose `cmdline` Pytop has no read access to.
            'cmdline_absent': The PID of the process that doesn’t have a `cmdline` file.
            'non_numeric_ppid': The PID of the process whose `status` contains “PPid” that has non-numeric symbols in it.
            'pids_of_multiple_number_ppid_proc': The PIDs of processes whose `status`es contain “PPid"s that consist of several alphanumeric symbol sequences, starting with a number, the first and second sequences separated by either a space or a tab.
            'ppid_of_multiple_numbers_space': The PPid of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a space.
            'ppid_of_multiple_numbers_tab': The PPid of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a tab.
            'wrong_threads_value': The PID of the process whose `status` contains “Threads” that has non-numeric symbols in it.
            'pids_of_multiple_number_threads_proc': The PIDs of processes whose `status`es contain “PPids” that consist of several alphanumeric symbol sequences, starting with a number, the first and second sequences separated by either a space or a tab.
            'threads_of_multiple_numbers_space': The “Threads” value consisting of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a space.
            'threads_of_multiple_numbers_tab': The “Threads” value of several alphanumeric symbol sequences, starting with a number, where the first and the second sequences are separated by a tab.
            'wrong_uid': The PIDs of processes with wrong `uid` values.
            'wrong_vmrss': The PIDs of processes with wrong `vmrss` values.
            'wrong_state': The PIDs of processes with wrong `state` values.
            'status_absent': The PID of the process without `status`.
            'wrong_read_bytes': The PIDs of processes with completely wrong `read_bytes` values.
            'wrong_write_bytes': The PIDs of processes with completely wrong `write_bytes` values.
            'pids_of_multiple_number_read_bytes_proc_space': The PIDs of processes with wrong `read_bytes` with a correct subvalue at the front separated from the rest of the value by a space.
            'pids_of_multiple_number_read_bytes_proc_tab': The PIDs of processes with wrong `read_bytes` with a correct subvalue at the front separated from the rest of the value by a tab.
            'pids_of_multiple_number_write_bytes_proc_space': The PIDs of processes with wrong `write_bytes` with a correct subvalue at the front separated from the rest of the value by a space.
            'pids_of_multiple_number_write_bytes_proc_tab': The PIDs of processes with wrong `write_bytes` with a correct subvalue at the front separated from the rest of the value by a space.
            'read_bytes_of_multiple_numbers_space': A wrong `read_bytes` with a correct subvalue at the front separated from the rest of the value by a space.
            'read_bytes_of_multiple_numbers_tab': A wrong `read_bytes` with a correct subvalue at the front separated from the rest of the value by a tab.
            'write_bytes_of_multiple_numbers_space': A wrong `write_bytes` with a correct subvalue at the front separated from the rest of the value by a space.
            'write_bytes_of_multiple_numbers_tab': A wrong `write_bytes` with a correct subvalue at the front separated from the rest of the value by a tab.
            'read_bytes_empty': The PID of the process with empty `read_bytes`.
            'write_bytes_empty': The PID of the process with empty `write_bytes`.
            'generate_process': A function to generate more processes dynamically. Puts the newly generated processes in the existing `/proc`-like directory.
    """

    proc = tmp_path / 'proc'
    proc.mkdir()

    proc_stat = proc / 'stat'
    proc_stat.touch()
    proc_stat_content = """\
    cpu  10132153 290696 3084719 46828483 16683 0 25195 0 175628 0
    cpu0 5066076 145348 1542359 23414241 8341 0 12597 0 87814 0
    cpu1 5066077 145348 1542360 23414242 8342 0 12598 0 87814 0
    page 5741 1808
    swap 1 0
    intr 1462898 1204 0 0 15 0 0 0 0 0 0 0 0 452 0 0
    disk_io: (2,0):(31,30,5764,1,2)
    ctxt 115315
    btime 1700000000
    processes 86031
    procs_running 6
    procs_blocked 2
    softirq 229245889 94 60001584 13619 5175704 2471304 28 51212741 59130143 0 51240672
    """
    proc_stat.write_text(proc_stat_content, 'utf-8')

    proc_uptime = proc / 'uptime'
    proc_uptime.touch()
    proc_uptime.write_text('468284.83 936569.66', 'utf-8')

    expected_pids: ExpectedPids = (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
    )

    def generate_process(
        pid: int,
        status: str | None = None,
        io: str | None = None,
        cmdline: str | None = None,
        stat: str | None = None,
        status_mode: int = 0o666,
        io_mode: int = 0o666,
        cmdline_mode: int = 0o666,
        stat_mode: int = 0o666,
    ) -> None:
        """Generates a process and puts it into the existing `/proc`-like directory already created by the `proc_helpers` fixture."""

        if pid <= 0:
            raise ValueError('PID must be greater than 0!')

        if (
            not (0 <= status_mode <= 0o7777)
            or not (0 <= io_mode <= 0o7777)
            or not (0 <= cmdline_mode <= 0o7777)
        ):
            raise ValueError(
                'Wrong UNIX mode! It must be between 0 and 0o7777.'
            )

        proc_pid = proc / str(pid)

        if proc_pid.exists():
            raise FileExistsError('Another process has already taken this PID!')
        else:
            proc_pid.mkdir()

        if status is not None:
            proc_pid_status = proc_pid / 'status'
            proc_pid_status.touch(status_mode, False)
            proc_pid_status.write_text(status, 'utf-8')

        if io is not None:
            proc_pid_io = proc_pid / 'io'
            proc_pid_io.touch(io_mode, False)
            proc_pid_io.write_text(io, 'utf-8')

        if cmdline is not None:
            proc_pid_cmdline = proc_pid / 'cmdline'
            proc_pid_cmdline.touch(cmdline_mode, False)
            proc_pid_cmdline.write_text(cmdline, 'utf-8')

        if stat is not None:
            proc_pid_stat = proc_pid / 'stat'
            proc_pid_stat.touch(stat_mode, False)
            proc_pid_stat.write_text(stat, 'utf-8')

    # STATICALLY GENERATED PROCESSES
    # Process 1
    # Normal process whose `status`, `io` and `cmdline` are accessible and each
    # of the files contains expected content and isn’t empty.
    proc_one = proc / '1'
    proc_one.mkdir()
    proc_one_status = proc_one / 'status'
    proc_one_status.touch()
    proc_one_status.write_text(
        'Name:\tpid one rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t1\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_one_io = proc_one / 'io'
    proc_one_io.touch()
    proc_one_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_one_cmdline = proc_one / 'cmdline'
    proc_one_cmdline.touch()
    proc_one_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 2
    # Process whose `status`, `cmdline` are accessible, `io` is not accessible
    # and whose `cmdline` is empty.
    proc_two = proc / '2'
    proc_two.mkdir()
    proc_two_status = proc_two / 'status'
    proc_two_status.touch()
    proc_two_status.write_text(
        'Name:\tpid two rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t2\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t24974 kB\n'
        'Threads:\t1\n'
    )
    proc_two_io = proc_two / 'io'
    proc_two_io.touch()
    proc_two_io.write_text('read_bytes: 1160525\nwrite_bytes: 55375', 'utf-8')
    proc_two_io.chmod(0o000)
    proc_two_cmdline = proc_two / 'cmdline'
    proc_two_cmdline.touch()

    # Process 3
    # Process whose `status`, `io` and `cmdline` are accessible and whose
    # `cmdline` contains a command with flags.
    proc_three = proc / '3'
    proc_three.mkdir()
    proc_three_status = proc_three / 'status'
    proc_three_status.touch()
    proc_three_status.write_text(
        'Name:\tpid three rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t3\n'
        'PPid:\t1\n'
        'Uid:\t1000\t1000\t1000\t1000\n'
        'VmRSS:\t25974 kB\n'
        'Threads:\t1\n'
    )
    proc_three_io = proc_three / 'io'
    proc_three_io.touch()
    proc_three_io.write_text('read_bytes: 1159526\nwrite_bytes: 54376', 'utf-8')
    proc_three_cmdline = proc_three / 'cmdline'
    proc_three_cmdline.touch()
    proc_three_cmdline.write_bytes(
        b'/usr/bin/start-something\x00with=some\x00flags\x001\x00'
    )

    # Process 4
    # Process whose `io`, `cmdline` are accessible, `status` is not accessible
    # and whose `cmdline` is empty.
    proc_four = proc / '4'
    proc_four.mkdir()
    proc_four_status = proc_four / 'status'
    proc_four_status.touch()
    proc_four_status.write_text(
        'Name:\tpid four rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t4\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t34473 kB\n'
        'Threads:\t1\n'
    )
    proc_four_status.chmod(0o000)
    proc_four_io = proc_four / 'io'
    proc_four_io.touch()
    proc_four_io.write_text('read_bytes: 1151340\nwrite_bytes: 46190', 'utf-8')
    proc_four_cmdline = proc_four / 'cmdline'
    proc_four_cmdline.touch()

    # Process 5
    # Each file is accessible to Pytop, `io` and `cmdline` contain expected
    # content, `status` and `cmdline` are empty.
    proc_five = proc / '5'
    proc_five.mkdir()
    proc_five_status = proc_five / 'status'
    proc_five_status.touch()
    proc_five_io = proc_five / 'io'
    proc_five_io.touch()
    proc_five_io.write_text('read_bytes: 134123\nwrite_bytes: 213499', 'utf-8')
    proc_five_cmdline = proc_five / 'cmdline'
    proc_five_cmdline.touch()

    # Process 6
    # Each file is accessible to Pytop, contains expected content, isn’t empty;
    # the value of the field `name` in `status` contains spaces and tabs.
    proc_six = proc / '6'
    proc_six.mkdir()
    proc_six_status = proc_six / 'status'
    proc_six_status.touch()
    name_with_spaces_and_tabs = 'some name\twith spaces\tand tabs'
    proc_six_status.write_text(
        f'Name:\t{name_with_spaces_and_tabs}\n'
        'State:\tS (sleeping)\n'
        'Pid:\t6\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_six_io = proc_six / 'io'
    proc_six_io.touch()
    proc_six_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_six_cmdline = proc_six / 'cmdline'
    proc_six_cmdline.touch()
    proc_six_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 7
    # `io` is absent, the rest of the files are accessible to Pytop, contain
    # expected content, aren’t empty.
    proc_seven = proc / '7'
    proc_seven.mkdir()
    proc_seven_status = proc_seven / 'status'
    proc_seven_status.touch()
    proc_seven_status.write_text(
        f'Name:\t{name_with_spaces_and_tabs}\n'
        'State:\tS (sleeping)\n'
        'Pid:\t7\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_seven_cmdline = proc_seven / 'cmdline'
    proc_seven_cmdline.touch()
    proc_seven_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 8
    # `status`, `io` are accessible, `cmdline` isn’t accessible to Pytop; each file contains expected content and isn’t empty.
    proc_eight = proc / '8'
    proc_eight.mkdir()
    proc_eight_status = proc_eight / 'status'
    proc_eight_status.touch()
    proc_eight_status.write_text(
        'Name:\tpid eight rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t8\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_eight_io = proc_eight / 'io'
    proc_eight_io.touch()
    proc_eight_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_eight_cmdline = proc_eight / 'cmdline'
    proc_eight_cmdline.touch()
    proc_eight_cmdline.write_text('/sbin/init', 'utf-8')
    proc_eight_cmdline.chmod(0o000)

    # Process 9
    # `cmdline` doesn’t exist; the rest of the files are accessible to Pytop,
    # contain expected content and aren’t empty.
    proc_nine = proc / '9'
    proc_nine.mkdir()
    proc_nine_status = proc_nine / 'status'
    proc_nine_status.touch()
    proc_nine_status.write_text(
        'Name:\tpid nine rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t9\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_nine_io = proc_nine / 'io'
    proc_nine_io.touch()
    proc_nine_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')

    # Process 10
    # Each file is accessible to Pytop; `status` contains “PPid” that has
    # non-numeric symbols in it, `io` and `cmdline` contains expected content;
    # no file is empty.
    proc_ten = proc / '10'
    proc_ten.mkdir()
    proc_ten_status = proc_ten / 'status'
    proc_ten_status.touch()
    proc_ten_status.write_text(
        'Name:\tpid ten rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t10\n'
        'PPid:\t0f3\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_ten_io = proc_ten / 'io'
    proc_ten_io.touch()
    proc_ten_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_ten_cmdline = proc_ten / 'cmdline'
    proc_ten_cmdline.touch()
    proc_ten_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 11
    # Each file is accessible to Pytop; `status` contains “PPid” that consists
    # of several alphanumeric symbol sequences, starting with a number, where
    # the first and the second sequences are separated by a space; `io` and
    # `cmdline` contain expected content; no file is empty.
    proc_eleven = proc / '11'
    proc_eleven.mkdir()
    proc_eleven_status = proc_eleven / 'status'
    proc_eleven_status.touch()
    ppid_of_multiple_numbers_space = '9 13 b 88 1 f9'
    proc_eleven_status.write_text(
        'Name:\tpid eleven rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t11\n'
        f'PPid:\t{ppid_of_multiple_numbers_space}\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_eleven_io = proc_eleven / 'io'
    proc_eleven_io.touch()
    proc_eleven_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_eleven_cmdline = proc_eleven / 'cmdline'
    proc_eleven_cmdline.touch()
    proc_eleven_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 12
    # Each file is accessible to Pytop; `status` contains “PPid” that consists
    # of several alphanumeric symbol sequences, starting with a number, where
    # the first and the second sequences are separated by a tab; `io` and
    # `cmdline` contain expected content; no file is empty.
    proc_twelve = proc / '12'
    proc_twelve.mkdir()
    proc_twelve_status = proc_twelve / 'status'
    proc_twelve_status.touch()
    ppid_of_multiple_numbers_tab = '9\t13 b 88 1 f9'
    proc_twelve_status.write_text(
        'Name:\tpid twelve rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t12\n'
        f'PPid:\t{ppid_of_multiple_numbers_tab}\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twelve_io = proc_twelve / 'io'
    proc_twelve_io.touch()
    proc_twelve_io.write_text('read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8')
    proc_twelve_cmdline = proc_twelve / 'cmdline'
    proc_twelve_cmdline.touch()
    proc_twelve_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 13
    # Each file is accessible to Pytop; `status` contains “Threads” that has
    # non-numeric symbols in it, `io` and `cmdline` contain expected content;
    # no file is empty.
    proc_thirteen = proc / '13'
    proc_thirteen.mkdir()
    proc_thirteen_status = proc_thirteen / 'status'
    proc_thirteen_status.touch()
    proc_thirteen_status.write_text(
        'Name:\tpid thirteen rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t13\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5f9\n'
    )
    proc_thirteen_io = proc_thirteen / 'io'
    proc_thirteen_io.touch()
    proc_thirteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_thirteen_cmdline = proc_thirteen / 'cmdline'
    proc_thirteen_cmdline.touch()
    proc_thirteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 14
    # Each file is accessible to Pytop; `status` contains “Threads” that consists
    # of several alphanumeric symbol sequences, starting with a number, where
    # the first and the second sequences are separated by a space; `io` and
    # `cmdline` contain expected content; no file is empty.
    proc_fourteen = proc / '14'
    proc_fourteen.mkdir()
    proc_fourteen_status = proc_fourteen / 'status'
    proc_fourteen_status.touch()
    threads_of_multiple_numbers_space = '9 13 b 88 1 f9'
    proc_fourteen_status.write_text(
        'Name:\tpid fourteen rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t14\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        f'Threads:\t{threads_of_multiple_numbers_space}\n'
    )
    proc_fourteen_io = proc_fourteen / 'io'
    proc_fourteen_io.touch()
    proc_fourteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_fourteen_cmdline = proc_fourteen / 'cmdline'
    proc_fourteen_cmdline.touch()
    proc_fourteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 15
    # Each file is accessible to Pytop; `status` contains “Threads” that consists
    # of several alphanumeric symbol sequences, starting with a number, where
    # the first and the second sequences are separated by a tab; `io` and
    # `cmdline` contain expected content; no file is empty.
    proc_fifteen = proc / '15'
    proc_fifteen.mkdir()
    proc_fifteen_status = proc_fifteen / 'status'
    proc_fifteen_status.touch()
    threads_of_multiple_numbers_tab = '9\t13 b 88 1 f9'
    proc_fifteen_status.write_text(
        'Name:\tpid fifteen rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t15\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        f'Threads:\t{threads_of_multiple_numbers_tab}\n'
    )
    proc_fifteen_io = proc_fifteen / 'io'
    proc_fifteen_io.touch()
    proc_fifteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_fifteen_cmdline = proc_fifteen / 'cmdline'
    proc_fifteen_cmdline.touch()
    proc_fifteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 16
    # Each file is accessible to Pytop, `status` has “Uid” in a wrong format, everything else is correct and non-empty.
    proc_sixteen = proc / '16'
    proc_sixteen.mkdir()
    proc_sixteen_status = proc_sixteen / 'status'
    proc_sixteen_status.touch()
    proc_sixteen_status.write_text(
        'Name:\tpid sixteen rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t16\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_sixteen_io = proc_sixteen / 'io'
    proc_sixteen_io.touch()
    proc_sixteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_sixteen_cmdline = proc_sixteen / 'cmdline'
    proc_sixteen_cmdline.touch()
    proc_sixteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 17
    # Each file is accessible to Pytop, `status` has “VmRSS” in a wrong format, everything else is correct and non-empty.
    proc_seventeen = proc / '17'
    proc_seventeen.mkdir()
    proc_seventeen_status = proc_seventeen / 'status'
    proc_seventeen_status.touch()
    proc_seventeen_status.write_text(
        'Name:\tpid seventeen rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t17\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031kB\n'
        'Threads:\t5\n'
    )
    proc_seventeen_io = proc_seventeen / 'io'
    proc_seventeen_io.touch()
    proc_seventeen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_seventeen_cmdline = proc_seventeen / 'cmdline'
    proc_seventeen_cmdline.touch()
    proc_seventeen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 18
    # Each file is accessible to Pytop, `status` has “State” in a wrong format, everything else is correct and non-empty.
    proc_eighteen = proc / '18'
    proc_eighteen.mkdir()
    proc_eighteen_status = proc_eighteen / 'status'
    proc_eighteen_status.touch()
    proc_eighteen_status.write_text(
        'Name:\tpid eighteen rand-name\n'
        'State:\tY (random)\n'
        'Pid:\t18\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_eighteen_io = proc_eighteen / 'io'
    proc_eighteen_io.touch()
    proc_eighteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_eighteen_cmdline = proc_eighteen / 'cmdline'
    proc_eighteen_cmdline.touch()
    proc_eighteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 19
    # `status` is absent, the rest of the files are accessible to Pytop, contain
    # expected content, aren’t empty.
    proc_nineteen = proc / '19'
    proc_nineteen.mkdir()
    proc_nineteen_io = proc_nineteen / 'io'
    proc_nineteen_io.touch()
    proc_nineteen_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_nineteen_cmdline = proc_nineteen / 'cmdline'
    proc_nineteen_cmdline.touch()
    proc_nineteen_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 20
    # `read_bytes` in `io` is completely wrong, everything else is as expected.
    proc_twenty = proc / '20'
    proc_twenty.mkdir()
    proc_twenty_status = proc_twenty / 'status'
    proc_twenty_status.touch()
    proc_twenty_status.write_text(
        'Name:\tpid twenty rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t20\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_io = proc_twenty / 'io'
    proc_twenty_io.touch()
    proc_twenty_io.write_text(
        'read_bytes: 1f234123\nwrite_bytes: 2134', 'utf-8'
    )
    proc_twenty_cmdline = proc_twenty / 'cmdline'
    proc_twenty_cmdline.touch()
    proc_twenty_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 21
    # `write_bytes` in `io` is completely wrong, everything else is as expected.
    proc_twenty_one = proc / '21'
    proc_twenty_one.mkdir()
    proc_twenty_one_status = proc_twenty_one / 'status'
    proc_twenty_one_status.touch()
    proc_twenty_one_status.write_text(
        'Name:\tpid twenty_one rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t21\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_one_io = proc_twenty_one / 'io'
    proc_twenty_one_io.touch()
    proc_twenty_one_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: 21a34', 'utf-8'
    )
    proc_twenty_one_cmdline = proc_twenty_one / 'cmdline'
    proc_twenty_one_cmdline.touch()
    proc_twenty_one_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 22
    # `read_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a space from everything else.
    proc_twenty_two = proc / '22'
    proc_twenty_two.mkdir()
    proc_twenty_two_status = proc_twenty_two / 'status'
    proc_twenty_two_status.touch()
    proc_twenty_two_status.write_text(
        'Name:\tpid twenty_two rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t22\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_two_io = proc_twenty_two / 'io'
    proc_twenty_two_io.touch()
    read_bytes_of_multiple_numbers_space = '12 3f 4123'
    proc_twenty_two_io.write_text(
        f'read_bytes: {read_bytes_of_multiple_numbers_space}\nwrite_bytes: 2134'
    )
    proc_twenty_two_cmdline = proc_twenty_two / 'cmdline'
    proc_twenty_two_cmdline.touch()
    proc_twenty_two_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 23
    # `read_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a tab from everything else.
    proc_twenty_three = proc / '23'
    proc_twenty_three.mkdir()
    proc_twenty_three_status = proc_twenty_three / 'status'
    proc_twenty_three_status.touch()
    proc_twenty_three_status.write_text(
        'Name:\tpid twenty_three rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t23\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_three_io = proc_twenty_three / 'io'
    proc_twenty_three_io.touch()
    read_bytes_of_multiple_numbers_tab = '1234\t123 7f'
    proc_twenty_three_io.write_text(
        f'read_bytes: {read_bytes_of_multiple_numbers_tab}\nwrite_bytes: 2134'
    )
    proc_twenty_three_cmdline = proc_twenty_three / 'cmdline'
    proc_twenty_three_cmdline.touch()
    proc_twenty_three_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 24
    # `write_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a space from everything else.
    proc_twenty_four = proc / '24'
    proc_twenty_four.mkdir()
    proc_twenty_four_status = proc_twenty_four / 'status'
    proc_twenty_four_status.touch()
    proc_twenty_four_status.write_text(
        'Name:\tpid twenty_four rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t24\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_four_io = proc_twenty_four / 'io'
    proc_twenty_four_io.touch()
    write_bytes_of_multiple_numbers_space = '2 134'
    proc_twenty_four_io.write_text(
        f'read_bytes: 1234123\nwrite_bytes: {write_bytes_of_multiple_numbers_space}'
    )
    proc_twenty_four_cmdline = proc_twenty_four / 'cmdline'
    proc_twenty_four_cmdline.touch()
    proc_twenty_four_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 25
    # `write_bytes` in `io` is wrong, but the value is a correct number at the front, separated by a tab from everything else.
    proc_twenty_five = proc / '25'
    proc_twenty_five.mkdir()
    proc_twenty_five_status = proc_twenty_five / 'status'
    proc_twenty_five_status.touch()
    proc_twenty_five_status.write_text(
        'Name:\tpid twenty_five rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t25\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_five_io = proc_twenty_five / 'io'
    proc_twenty_five_io.touch()
    write_bytes_of_multiple_numbers_tab = '2\t134'
    proc_twenty_five_io.write_text(
        f'read_bytes: 1234123\nwrite_bytes: {write_bytes_of_multiple_numbers_tab}'
    )
    proc_twenty_five_cmdline = proc_twenty_five / 'cmdline'
    proc_twenty_five_cmdline.touch()
    proc_twenty_five_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 26
    # `read_bytes` in `io` is empty.
    proc_twenty_six = proc / '26'
    proc_twenty_six.mkdir()
    proc_twenty_six_status = proc_twenty_six / 'status'
    proc_twenty_six_status.touch()
    proc_twenty_six_status.write_text(
        'Name:\tpid twenty_six rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t26\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_six_io = proc_twenty_six / 'io'
    proc_twenty_six_io.touch()
    proc_twenty_six_io.write_text('read_bytes: \nwrite_bytes: 2134', 'utf-8')
    proc_twenty_six_cmdline = proc_twenty_six / 'cmdline'
    proc_twenty_six_cmdline.touch()
    proc_twenty_six_cmdline.write_text('/sbin/init', 'utf-8')

    # Process 27
    # `write_bytes` in `io` is empty.
    proc_twenty_seven = proc / '27'
    proc_twenty_seven.mkdir()
    proc_twenty_seven_status = proc_twenty_seven / 'status'
    proc_twenty_seven_status.touch()
    proc_twenty_seven_status.write_text(
        'Name:\tpid twenty_seven rand-name\n'
        'State:\tS (sleeping)\n'
        'Pid:\t27\n'
        'PPid:\t0\n'
        'Uid:\t0\t0\t0\t0\n'
        'VmRSS:\t15031 kB\n'
        'Threads:\t5\n'
    )
    proc_twenty_seven_io = proc_twenty_seven / 'io'
    proc_twenty_seven_io.touch()
    proc_twenty_seven_io.write_text(
        'read_bytes: 1234123\nwrite_bytes: ', 'utf-8'
    )
    proc_twenty_seven_cmdline = proc_twenty_seven / 'cmdline'
    proc_twenty_seven_cmdline.touch()
    proc_twenty_seven_cmdline.write_text('/sbin/init', 'utf-8')

    return {
        'dir': proc,
        'io_no_read': (2,),
        'status_no_read': (4,),
        'status_empty': (5,),
        'status_name_spaces_and_tabs': 6,
        'name_with_spaces_and_tabs': name_with_spaces_and_tabs,
        'io_absent': 7,
        'cmdline_no_read': 8,
        'cmdline_absent': 9,
        'non_numeric_ppid': 10,
        'pids_of_multiple_number_ppid_proc': (11, 12),
        'ppid_of_multiple_numbers_space': ppid_of_multiple_numbers_space,
        'ppid_of_multiple_numbers_tab': ppid_of_multiple_numbers_tab,
        'wrong_threads_value': 13,
        'pids_of_multiple_number_threads_proc': (14, 15),
        'threads_of_multiple_numbers_space': threads_of_multiple_numbers_space,
        'threads_of_multiple_numbers_tab': threads_of_multiple_numbers_tab,
        'wrong_state': (18,),
        'wrong_uid': (16,),
        'wrong_vmrss': (17,),
        'status_absent': 19,
        'wrong_read_bytes': (20, 26),
        'wrong_write_bytes': (21, 27),
        'pids_of_multiple_number_read_bytes_proc_space': (22,),
        'pids_of_multiple_number_read_bytes_proc_tab': (23,),
        'pids_of_multiple_number_write_bytes_proc_space': (24,),
        'pids_of_multiple_number_write_bytes_proc_tab': (25,),
        'read_bytes_of_multiple_numbers_space': read_bytes_of_multiple_numbers_space,
        'read_bytes_of_multiple_numbers_tab': read_bytes_of_multiple_numbers_tab,
        'write_bytes_of_multiple_numbers_space': write_bytes_of_multiple_numbers_space,
        'write_bytes_of_multiple_numbers_tab': write_bytes_of_multiple_numbers_tab,
        'read_bytes_empty': 26,
        'write_bytes_empty': 27,
        'expected_pids': expected_pids,
        'generate_process': generate_process,
    }


@pytest.fixture(autouse=True, scope='module')
def mock_system_calls() -> Generator[None]:
    """Mocks `os.sysconf['SC_CLK_TCK']` to return 100 and `os.cpu_count()` to return 2. Works across the entire module, cleans up after itsef."""

    mp = pytest.MonkeyPatch()

    def sysconf_mock(name: str | int):
        return (
            100
            if name == 'SC_CLK_TCK' or name == os.sysconf_names['SC_CLK_TCK']
            else -1
        )

    mp.setattr('os.sysconf', sysconf_mock)
    mp.setattr('os.cpu_count', lambda: 2)

    yield

    mp.undo()
