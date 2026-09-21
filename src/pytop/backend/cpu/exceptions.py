"""Errors and warnings specific to the `cpu` module."""

from pathlib import Path

from pytop.backend.exceptions import (
    FileNotFoundWarning,
    IndexWarning,
    PermissionWarning,
    ValueWarning,
)


class ProcUptimeFileNotFoundWarning(FileNotFoundWarning): ...


class ProcUptimePermissionWarning(PermissionWarning): ...


class ProcUptimeValueWarning(ValueWarning): ...


class ProcUptimeIndexWarning(IndexWarning): ...


class ProcLoadavgFileNotFoundWarning(FileNotFoundWarning): ...


class ProcLoadavgPermissionWarning(PermissionWarning): ...


class ProcLoadavgValueWarning(ValueWarning): ...


class ProcLoadavgIndexWarning(IndexWarning): ...


class ProcCpuinfoFileNotFoundWarning(FileNotFoundWarning): ...


class ProcCpuinfoPermissionWarning(PermissionWarning): ...


class ProcCpuinfoValueWarning(ValueWarning): ...


class ProcCpuinfoIndexWarning(IndexWarning): ...


class ProcStatFileNotFoundWarning(FileNotFoundWarning): ...


class ProcStatPermissionWarning(PermissionWarning): ...


class ProcStatValueWarning(ValueWarning): ...


class ProcStatIndexWarning(IndexWarning): ...


class PowerTelemetrySensorNotFoundWarning(FileNotFoundWarning):
    def __init__(self, sensor_name: str, filepath: Path):
        self.filepath = filepath
        msg = f'Sensor {sensor_name} not found at {filepath}.'
        super().__init__(filepath, msg)


class PowerTelemetrySensorPermissionWarning(PermissionWarning):
    def __init__(self, sensor_name: str, filepath: Path):
        self.filepath = filepath
        msg = f'Permission denied for sensor {sensor_name} at {filepath}.'
        super().__init__(filepath, msg)


class PowerTelemetrySensorValueWarning(ValueWarning):
    def __init__(self, value: str, filepath: Path):
        msg = f'Unlikely sensor value in file {filepath}: {value}.'
        super().__init__(0, msg)
