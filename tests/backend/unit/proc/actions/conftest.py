import os
from typing import TypedDict

import pytest

PERMISSION_DENIED_PID = 1
PROCESS_NOT_FOUND_PID = 85395

# =============================================================================
# MOCK FOR os.kill()
# =============================================================================


class OsKillCall(TypedDict):
    pid: int
    sig: int


OsKillCalls = list[OsKillCall]


@pytest.fixture
def os_kill_calls(monkeypatch: pytest.MonkeyPatch) -> OsKillCalls:
    """Mocks `os.kill`. The mocked function appends an `OsKillMockCall`
    instance to an internal list. That list is returned from the fixture."""

    calls: OsKillCalls = []

    def os_kill_mocked(pid: int, sig: int) -> None:
        calls.append(OsKillCall(pid=pid, sig=sig))

        if pid == PERMISSION_DENIED_PID:
            raise PermissionError

        if pid == PROCESS_NOT_FOUND_PID:
            raise ProcessLookupError

    monkeypatch.setattr(os, 'kill', os_kill_mocked)

    return calls


# =============================================================================
# MOCK FOR os.setpriority()
# =============================================================================


class OsSetpriorityCall(TypedDict):
    which: int
    who: int
    priority: int


OsSetpriorityCalls = list[OsSetpriorityCall]


@pytest.fixture
def os_setpriority_calls(monkeypatch: pytest.MonkeyPatch) -> OsSetpriorityCalls:
    """Mocks `os.setpriority`. The mocked function appends an
    `OsSetpriorityMockCall` instance to an internal list. That list is returned
    from the fixture."""

    calls: OsSetpriorityCalls = []

    def os_setpriority_mocked(which: int, who: int, priority: int) -> None:
        calls.append(OsSetpriorityCall(which=which, who=who, priority=priority))

        if which == os.PRIO_PROCESS and who == PERMISSION_DENIED_PID:
            raise PermissionError

        if which == os.PRIO_PROCESS and who == PROCESS_NOT_FOUND_PID:
            raise ProcessLookupError

    monkeypatch.setattr(os, 'setpriority', os_setpriority_mocked)

    return calls
