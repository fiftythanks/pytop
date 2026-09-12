import os

import pytest

from pytop.backend.proc.actions.renice import renice
from tests.backend.unit.proc.actions.conftest import OsSetpriorityCalls


@pytest.mark.parametrize('priority', range(-20, 20))
def test_accepts_correct_priority(
    priority: int, os_setpriority_calls: OsSetpriorityCalls
):
    # ARRANGE
    pid = 99999

    # ACT
    success = renice(pid, priority)

    # ASSERT
    assert success is True


@pytest.mark.parametrize('priority', range(-20, 20))
def test_renices_correctly(
    priority: int, os_setpriority_calls: OsSetpriorityCalls
):
    # ARRANGE
    pid = 12345

    # ACT
    renice(pid, priority)

    # ASSERT
    target_call = os_setpriority_calls[0]
    assert target_call['priority'] == priority
    assert target_call['who'] == pid
    assert target_call['which'] == os.PRIO_PROCESS


@pytest.mark.parametrize('priority', [99, -351, -21, 999])
def test_rejects_incorrect_priority(
    priority: int, os_setpriority_calls: OsSetpriorityCalls
):
    # ARRANGE
    pid = 123483

    with pytest.raises(ValueError):
        renice(pid, priority)
