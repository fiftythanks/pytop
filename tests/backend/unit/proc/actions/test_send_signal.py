from signal import Signals

import pytest

from pytop.backend.proc.actions.send_signal import send_signal
from tests.backend.unit.proc.actions.conftest import OsKillCalls


@pytest.mark.parametrize('sig', [*list(Signals)[1:32]])
def test_accepts_relevant_signals(
    mock_os_kill_calls: OsKillCalls, sig: Signals
):
    # ARRANGE
    pid = 9999999

    # ACT
    success = send_signal(pid, sig)

    # ASSERT
    assert success is True


@pytest.mark.parametrize('sig', list(Signals)[1:32])
def test_sends_relevant_signals(mock_os_kill_calls: OsKillCalls, sig: Signals):
    # ARRANGE
    pid = 9999999

    # ACT
    send_signal(pid, sig)

    # ASSERT
    assert mock_os_kill_calls[0]['pid'] == pid
    assert mock_os_kill_calls[0]['sig'] == sig.value


@pytest.mark.parametrize('sig', list(Signals)[32:])
def test_rejects_irrelevant_signals(
    mock_os_kill_calls: OsKillCalls, sig: Signals
):
    # ARRANGE
    pid = 999999

    # ASSERT
    with pytest.raises(ValueError):
        send_signal(pid, sig)
