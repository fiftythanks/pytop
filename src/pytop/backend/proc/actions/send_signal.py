import os
from signal import Signals

from pytop.backend.proc.actions.errors import (
    ProcActionProcessLookupError,
    SignalPermissionError,
)


def send_signal(pid: int, sig: Signals) -> bool:
    relevant_signals = list(Signals)[1:32]
    if sig not in relevant_signals:
        raise ValueError('Signals not in the 1...31 range are not allowed!')

    try:
        os.kill(pid, sig.value)
    except PermissionError:
        raise SignalPermissionError(pid, sig)
    except ProcessLookupError:
        raise ProcActionProcessLookupError(pid)

    return True
