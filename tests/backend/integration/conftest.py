import sys
from collections.abc import Generator
from subprocess import Popen, TimeoutExpired

import pytest


@pytest.fixture
def sacrificial_process() -> Generator[Popen[bytes]]:
    """Creates and returns a child process that sleeps for 60 seconds before exiting."""

    process: Popen[bytes] | None = None

    try:
        process = Popen([sys.executable, '-c', 'import time; time.sleep(60)'])

        yield process
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(1.0)
            except TimeoutExpired:
                process.kill()
                process.wait()
