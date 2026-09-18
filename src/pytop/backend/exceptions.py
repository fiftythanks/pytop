"""Backend-wide exceptions and warnings."""

from pathlib import Path
from typing import Any


class FileNotFoundWarning(UserWarning):
    """Raised when a non-critical file is missing from the file system."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

        msg = f'File {self.filepath.resolve()} not found.'
        super().__init__(msg)


class PermissionWarning(UserWarning):
    """Raised when a non-critical file cannot be accessed due to permission issues."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

        msg = f'Permission denied for file {self.filepath.resolve()}.'
        super().__init__(msg)


class ValueWarning(UserWarning):
    """Raised when a non-critical value is invalid or unexpected."""

    def __init__(self, value: Any = None, message: str = 'Invalid value'):
        if value is None:
            super().__init__(message)
            return

        self.value = value
        msg = f'{message}: {self.value}'
        super().__init__(msg)


class IndexWarning(UserWarning):
    """Raised when an index is out of bounds or invalid."""

    def __init__(
        self, index: int | None = None, message: str = 'Index out of bounds'
    ):
        if index is None:
            super().__init__(message)
            return

        self.index = index
        msg = f'{message}: {self.index}'
        super().__init__(msg)
