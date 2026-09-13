import os
from subprocess import Popen

from pytop.backend.proc.actions.errors import Signals
from pytop.backend.proc.actions.renice import renice
from pytop.backend.proc.actions.send_signal import send_signal
from pytop.backend.proc.create_process_monitor import create_process_monitor
from pytop.shared.process import State


def test_sees_real_processes(sacrificial_process: Popen[bytes]):
    # ACT
    get_processes = create_process_monitor()
    processes = get_processes()

    # ASSERT
    assert sacrificial_process.pid in processes


def test_sanity(sacrificial_process: Popen[bytes]):
    """The process must have `python` in its name and its state must be Sleep."""

    # ARRANGE
    get_processes = create_process_monitor()
    processes = get_processes()

    # ACT
    target_process = processes[sacrificial_process.pid]

    # ASSERT
    assert (
        target_process.name is not None
        and target_process.name.find('python') != -1
    )
    assert target_process.state == State.SLEEPING


def test_renice_changes_priority(sacrificial_process: Popen[bytes]):
    # ARRANGE
    pid = sacrificial_process.pid

    # ACT
    final_priority = 5

    initial_priority = os.getpriority(os.PRIO_PROCESS, pid)
    if initial_priority == 5:
        final_priority = 6
        renice(pid, 6)
    else:
        renice(pid, 5)

    # ASSERT
    assert os.getpriority(os.PRIO_PROCESS, pid) == final_priority


def test_send_signal_terminates_process(sacrificial_process: Popen[bytes]):
    # ARRANGE
    pid = sacrificial_process.pid

    # ACT
    send_signal(pid, Signals.SIGTERM)

    # ASSERT
    assert sacrificial_process.wait() == -Signals.SIGTERM


def test_send_signal_kills_process(sacrificial_process: Popen[bytes]):
    # ARRANGE
    pid = sacrificial_process.pid

    # ACT
    send_signal(pid, Signals.SIGKILL)

    # ASSERT
    assert sacrificial_process.wait() == -Signals.SIGKILL
