from dataclasses import dataclass


@dataclass(frozen=True)
class CoreStats:
    """Holds all CPU data Pytop was able to find in sysfs **for an individual core**."""

    id: int
    frequency: float
    usage_percent: float
    temperature_celsius: float


@dataclass(frozen=True)
class CpuStats:
    """Holds all CPU data Pytop was able to find in sysfs."""

    name: str | None
    uptime_sec: float | None
    load_avg_1min: float | None
    load_avg_5min: float | None
    load_avg_15min: float | None
    usage_percent: float | None
    power_consumption_watt: float | None
    sensors: dict[str, float]
    core_stats: dict[int, CoreStats]
