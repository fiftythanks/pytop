from signal import Signals

import pytest

from pytop.backend.proc.actions.errors import (
    ProcActionProcessLookupError,
    SignalPermissionError,
)
from pytop.backend.proc.actions.send_signal import send_signal
from tests.backend.unit.proc.actions.conftest import (
    PERMISSION_DENIED_PID,
    PROCESS_NOT_FOUND_PID,
    OsKillCalls,
)


@pytest.mark.parametrize('sig', [*list(Signals)[1:32]])
def test_accepts_relevant_signals(os_kill_calls: OsKillCalls, sig: Signals):
    # ARRANGE
    pid = 9999999

    # ACT
    success = send_signal(pid, sig)

    # ASSERT
    assert success is True


@pytest.mark.parametrize('sig', list(Signals)[1:32])
def test_sends_relevant_signals(os_kill_calls: OsKillCalls, sig: Signals):
    # ARRANGE
    pid = 9999999

    # ACT
    send_signal(pid, sig)

    # ASSERT
    assert os_kill_calls[0]['pid'] == pid
    assert os_kill_calls[0]['sig'] == sig.value


@pytest.mark.parametrize('sig', list(Signals)[32:])
def test_rejects_irrelevant_signals(os_kill_calls: OsKillCalls, sig: Signals):
    # ARRANGE
    pid = 999999

    # ASSERT
    with pytest.raises(ValueError):
        send_signal(pid, sig)


@pytest.mark.parametrize('sig', list(Signals)[1:32])
def test_raises_if_no_right_to_send_signal(
    os_kill_calls: OsKillCalls, sig: Signals
):
    # ASSERT
    with pytest.raises(SignalPermissionError):
        send_signal(PERMISSION_DENIED_PID, sig)


@pytest.mark.parametrize('sig', list(Signals)[1:32])
def test_raises_if_no_process_found(os_kill_calls: OsKillCalls, sig: Signals):
    with pytest.raises(ProcActionProcessLookupError):
        send_signal(PROCESS_NOT_FOUND_PID, sig)
