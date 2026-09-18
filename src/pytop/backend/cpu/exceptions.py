"""Errors and warnings specific to the `cpu` module."""

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
