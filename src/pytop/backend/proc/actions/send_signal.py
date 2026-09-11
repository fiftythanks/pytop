import os
from signal import Signals


def send_signal(pid: int, sig: Signals) -> bool:
    relevant_signals = list(Signals)[1:32]
    if sig not in relevant_signals:
        raise ValueError('Signals not in the 1...31 range are not allowed!')

    # TODO: Handle edge cases when integration testing:
    #   - No permission to execute a signal on a process
    #   - Process already dead or something else that prevents correct signal receiving
    os.kill(pid, sig.value)

    return True
