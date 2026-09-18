import os
from collections.abc import Generator

from pytest import MonkeyPatch, fixture


@fixture(autouse=True, scope='module')
def mock_system_calls() -> Generator[None]:
    """Mocks `os.sysconf['SC_CLK_TCK']` to return 100 and `os.cpu_count()` to return 2. Works across the entire module, cleans up after itsef."""

    mp = MonkeyPatch()

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
