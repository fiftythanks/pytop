import os
from typing import TypedDict

import pytest


class MockCall(TypedDict):
    pid: int
    sig: int


MockCalls = list[MockCall]


@pytest.fixture
def mock_os_kill_calls(monkeypatch: pytest.MonkeyPatch) -> MockCalls:
    """Mocks `os.kill`. The mocked function appends a `Call` instance to an
    internal list. That list is returned from the fixture."""

    calls: list[MockCall] = []

    def os_kill_mocked(pid: int, sig: int) -> None:
        calls.append(MockCall(pid=pid, sig=sig))

    monkeypatch.setattr(os, 'kill', os_kill_mocked)

    return calls
