"""This module is internal implementation details of discover_power_telemetry_sensors()."""

import warnings
from pathlib import Path

from pytop.backend.cpu.exceptions import PowerTelemetrySensorValueWarning
from pytop.backend.cpu.power_telemetry.exceptions import (
    EnergyUjNotFoundWarning,
    EnergyUjPermissionWarning,
    ZoneFileEmptyWarning,
    ZoneNameNotFoundWarning,
    ZoneNamePermissionWarning,
)
from pytop.backend.cpu.power_telemetry.sensors import EnergySensor


def create_and_append_powercap_energy_sensor(
    backend: str, zone_path: Path, energy_sensors: list[EnergySensor]
):
    """Appends only those sensors that have `energy_uj >= 0`."""

    zone_name_path = zone_path / 'name'

    try:
        zone_name = zone_name_path.read_text('utf-8')

        # TODO: Fall back to the zone dir name in the UI.
        if zone_name == '':
            warnings.warn(
                ZoneFileEmptyWarning(backend, zone_path.name, zone_name_path)
            )
    except FileNotFoundError:
        warnings.warn(
            ZoneNameNotFoundWarning(backend, zone_path.name, zone_name_path)
        )
        zone_name = ''
    except PermissionError:
        warnings.warn(
            ZoneNamePermissionWarning(backend, zone_path.name, zone_name_path)
        )
        zone_name = ''

    energy_uj_path = zone_path / 'energy_uj'

    try:
        energy_uj = energy_uj_path.read_text('utf-8')

        if energy_uj == '':
            warnings.warn(
                ZoneFileEmptyWarning(backend, zone_path.name, energy_uj_path)
            )
            return

        # 0 can be a real value, though very unlikely, so I decided to
        # create a sensor instance and include it into sensors.
        if energy_uj == '0':
            warnings.warn(
                PowerTelemetrySensorValueWarning(energy_uj, energy_uj_path)
            )

        try:
            if int(energy_uj) < 0:
                warnings.warn(
                    PowerTelemetrySensorValueWarning(energy_uj, energy_uj_path)
                )
                return
        except ValueError:
            warnings.warn(
                PowerTelemetrySensorValueWarning(energy_uj, energy_uj_path)
            )
            return

    except FileNotFoundError:
        warnings.warn(
            EnergyUjNotFoundWarning(backend, zone_path.name, energy_uj_path)
        )
        return
    except PermissionError:
        warnings.warn(
            EnergyUjPermissionWarning(backend, zone_path.name, energy_uj_path)
        )
        return

    sensor = EnergySensor(zone_name, energy_uj_path)

    energy_sensors.append(sensor)
