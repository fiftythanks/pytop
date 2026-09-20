from pathlib import Path

from pytop.backend.exceptions import (
    FileNotFoundWarning,
    PermissionWarning,
    ValueWarning,
)


class PowercapNotFoundWarning(FileNotFoundWarning):
    def __init__(self, powercap_path: Path):
        super().__init__(
            powercap_path, 'Powercap framework isn’t found in the system.'
        )


class PowercapInterfaceNotFoundWarning(FileNotFoundWarning):
    def __init__(self, powercap_path: Path):
        msg = 'Neither Intel RAPL nor ARM SCMI powercap interfaces were found in the system.'
        super().__init__(powercap_path, msg)


class ZoneNameNotFoundWarning(FileNotFoundWarning):
    def __init__(self, backend: str, zone_dir_name: str, zone_name_path: Path):
        msg = f'{backend} zone {zone_dir_name} has no name file. Falling back to an empty name.'
        super().__init__(filepath=zone_name_path, message=msg)


class ZoneNamePermissionWarning(PermissionWarning):
    def __init__(self, backend: str, zone_dir_name: str, zone_name_path: Path):
        msg = f'{backend} zone {zone_dir_name} has a name file that cannot be read due to permission issues. Falling back to an empty name.'
        super().__init__(filepath=zone_name_path, message=msg)


class ZoneFileEmptyWarning(ValueWarning):
    def __init__(self, backend: str, zone_dir_name: str, empty_file_path: Path):
        msg = f'{backend} zone {zone_dir_name} has the {empty_file_path.name} file empty.'
        super().__init__(message=msg)


class EnergyUjNotFoundWarning(FileNotFoundWarning):
    def __init__(self, backend: str, zone_dir_name: str, energy_uj_path: Path):
        msg = f'{backend} zone {zone_dir_name} has no energy_uj file.'
        super().__init__(filepath=energy_uj_path, message=msg)


class EnergyUjPermissionWarning(PermissionWarning):
    def __init__(self, backend: str, zone_dir_name: str, energy_uj_path: Path):
        msg = f'{backend} zone {zone_dir_name} has an energy_uj file that cannot be read due to permission issues.'
        super().__init__(energy_uj_path, msg)


class PowerTelemetrySensorValueWarning(ValueWarning):
    def __init__(self, value: str, sensor_value_source_path: Path):
        msg = f'Unlikely sensor value in file {sensor_value_source_path}: {value}.'
        super().__init__(0, msg)
