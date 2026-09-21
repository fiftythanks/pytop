from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class PowerTelemetrySensor:
    """Generic class for any power or energy sensor.

    Any power or energy sensor related to the `cpu` module found in the system
    is an instance of either this class or a subclass of it.
    """

    name: str
    path: Path
    type: Literal['power', 'energy']


@dataclass(frozen=True)
class PowerSensor(PowerTelemetrySensor):
    """Strictly power (microwatt) sensors."""

    type: Literal['power'] = 'power'


@dataclass(frozen=True)
class EnergySensor(PowerTelemetrySensor):
    """Strictly energy (microjoule) sensors."""

    type: Literal['energy'] = 'energy'


@dataclass(frozen=True)
class PowerTelemetrySensors:
    energy_sensors: list[EnergySensor]
    power_sensors: list[PowerSensor]
