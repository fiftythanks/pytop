import getpass
from signal import Signals


class ProcActionProcessLookupError(ProcessLookupError):
    """Process not found, raised by a `proc` action."""

    def __init__(self, pid: int) -> None:
        super().__init__(f'Couldn’t find a process with PID {pid}.')


class ProcActionPermissionError(PermissionError):
    """Permission to execute a `proc` action denied."""

    def __init__(
        self, message: str = 'Permission to execute this process action denied.'
    ) -> None:
        super().__init__(message)


class SignalPermissionError(ProcActionPermissionError):
    """No permission to send a signal to a process."""

    def __init__(self, pid: int, sig: Signals) -> None:
        super().__init__(
            f'User {getpass.getuser()} has no permission to send the {sig.name} signal to the process {pid}.'
        )


class RenicePermissionError(ProcActionPermissionError):
    """Permission to renice a process denied."""

    def __init__(self, pid: int) -> None:
        super().__init__(
            f'User {getpass.getuser()} has no permission to renice the process {pid}'
        )
