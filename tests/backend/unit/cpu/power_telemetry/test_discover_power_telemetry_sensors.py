from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pytest import fixture, mark, warns

from pytop.backend.cpu.power_telemetry.discover_power_telemetry_sensors import (
    discover_power_telemetry_sensors,
)
from pytop.backend.cpu.power_telemetry.exceptions import (
    EnergyUjNotFoundWarning,
    EnergyUjPermissionWarning,
    HwmonNotFoundWarning,
    PowercapInterfaceNotFoundWarning,
    PowercapNotFoundWarning,
    PowerTelemetryNotFoundWarning,
    PowerTelemetrySensorValueWarning,
    ZoneFileEmptyWarning,
    ZoneNameNotFoundWarning,
    ZoneNamePermissionWarning,
)


@fixture
def sys_path(tmp_path: Path) -> Path:
    sys_path = tmp_path / 'sys'
    sys_path.mkdir()
    return sys_path


@fixture
def powercap_path(sys_path: Path) -> Path:
    powercap_path = sys_path / 'class' / 'powercap'
    powercap_path.mkdir(parents=True)
    return powercap_path


@fixture
def hwmon_path(sys_path: Path) -> Path:
    hwmon_path = sys_path / 'class' / 'hwmon'
    hwmon_path.mkdir(parents=True)
    return hwmon_path


@dataclass
class PowercapZone:
    relative_path: Path
    """Relative to the framework root directory."""
    energy_uj: int | str | None = None
    """Energy consumption, in µJ."""
    energy_uj_mode: int = 0o666
    name: str | None = None
    name_mode: int = 0o666


some_intel_rapl_zones: list[PowercapZone] = [
    PowercapZone(
        relative_path=Path('intel-rapl:0'),
        energy_uj=30901899345,
        name='package-0',
    ),
    PowercapZone(
        relative_path=Path('intel-rapl:0/intel-rapl:0:1'),
        energy_uj=8804986919,
        name='core',
    ),
    PowercapZone(
        relative_path=Path('intel-rapl:0/intel-rapl:0:2'),
        energy_uj=7332626736,
        name='uncore',
    ),
    PowercapZone(
        relative_path=Path('intel-rapl:1'), energy_uj=4517528230, name='psys'
    ),
    PowercapZone(
        relative_path=Path('intel-rapl:2'), energy_uj=2493134, name='dmem'
    ),
]

some_arm_scmi_zones: list[PowercapZone] = [
    PowercapZone(
        relative_path=Path('arm-scmi:0'),
        energy_uj=12345678,
        name='scmi-package-0',
    ),
    PowercapZone(
        relative_path=Path('arm-scmi:0/arm-scmi:0:1'),
        energy_uj=456789,
        name='scmi-core',
    ),
    PowercapZone(
        relative_path=Path('arm-scmi:0/arm-scmi:0:2'),
        energy_uj=987654,
        name='scmi-big-core',
    ),
    PowercapZone(
        relative_path=Path('arm-scmi:1'),
        energy_uj=87654321,
        name='scmi-package-1',
    ),
]


class MockPowercapBackend(Protocol):
    def __call__(self, dir_name: str, *zones: PowercapZone) -> Path: ...


@fixture
def mock_powercap_backend(powercap_path: Path) -> MockPowercapBackend:
    def _mock(dir_name: str, *zones: PowercapZone) -> Path:
        backend_path = powercap_path / dir_name
        backend_path.mkdir(parents=True, exist_ok=True)

        for zone in zones:
            zone_path = backend_path / zone.relative_path
            zone_path.mkdir(parents=True, exist_ok=True)

            if zone.name is not None:
                zone_name_path = zone_path / 'name'
                zone_name_path.touch()
                zone_name_path.write_text(zone.name, 'utf-8')
                zone_name_path.chmod(zone.name_mode)

            if zone.energy_uj is not None:
                zone_energy_uj_path = zone_path / 'energy_uj'
                zone_energy_uj_path.touch()
                zone_energy_uj_path.write_text(str(zone.energy_uj), 'utf-8')
                zone_energy_uj_path.chmod(zone.energy_uj_mode)

        return backend_path

    return _mock


def test_power_telemetry_not_found(sys_path: Path):
    # ASSERT
    with warns(PowerTelemetryNotFoundWarning):
        discover_power_telemetry_sensors(sys_path)


class TestPowercap:
    """Tests related to the `powercap` dir search."""

    def test_warns_if_no_powercap_dir(self, sys_path: Path):
        with warns(PowercapNotFoundWarning):
            discover_power_telemetry_sensors(sys_path)

    def test_warns_neither_interface_found(
        self, sys_path: Path, powercap_path: Path
    ):
        with warns(PowercapInterfaceNotFoundWarning):
            discover_power_telemetry_sensors(sys_path)


@mark.parametrize(
    'backend,dir_name,zone_prefix,all_zones',
    [
        ('Intel RAPL', 'intel-rapl', 'intel-rapl:', some_intel_rapl_zones),
        ('ARM SCMI', 'arm-scmi', 'arm-scmi:', some_arm_scmi_zones),
    ],
)
class TestPowercapInterfaces:
    """Parameterised test suite covering all powercap interfaces."""

    def test_interface_paths(
        self,
        sys_path: Path,
        mock_powercap_backend: MockPowercapBackend,
        backend: str,
        dir_name: str,
        zone_prefix: str,
        all_zones: list[PowercapZone],
    ):
        # ARRANGE
        backend_path = mock_powercap_backend(dir_name, *all_zones)

        # ACT
        sensors = discover_power_telemetry_sensors(sys_path)

        # ASSERT
        for zone in all_zones:
            target_sensor = next(
                (
                    s
                    for s in sensors.energy_sensors
                    if s.name == zone.name
                    and s.path.samefile(backend_path / zone.relative_path)
                ),
                None,
            )
            assert target_sensor is not None

    class TestErrors:
        class TestZoneName:
            class TestIsEmpty:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='',
                        ),
                    )

                    # ASSERT
                    with warns(ZoneFileEmptyWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_is_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='',
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 1
                    assert sensors.energy_sensors[0].name == ''

            class TestFileNotFound:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'), energy_uj=0
                        ),
                    )

                    # ASSERT
                    with warns(ZoneNameNotFoundWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_falls_back_to_empty(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'), energy_uj=0
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert sensors.energy_sensors[0].name == ''

            class TestPermissionError:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                            name_mode=0o000,
                        ),
                    )

                    # ASSERT
                    with warns(ZoneNamePermissionWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_falls_back_to_empty(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                            name_mode=0o000,
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert sensors.energy_sensors[0].name == ''

        class TestEnergyUj:
            class TestIsEmpty:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj='',
                            name='zone',
                        ),
                    )

                    # ASSERT
                    with warns(ZoneFileEmptyWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_not_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj='',
                            name='zone',
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 0

            class TestIsNull:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                        ),
                    )

                    # ASSERT
                    with warns(PowerTelemetrySensorValueWarning):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_is_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 1
                    assert sensors.energy_sensors[0].name == 'zone'

            class TestIsLessThanNull:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=-1,
                            name='zone',
                        ),
                    )

                    # ASSERT
                    with warns(PowerTelemetrySensorValueWarning):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_not_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=-1,
                            name='zone',
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 0

            class TestNonNumberValue:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj='not-a-number',
                            name='zone',
                        ),
                    )

                    # ASSERT
                    with warns(PowerTelemetrySensorValueWarning):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_not_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj='not-a-number',
                            name='zone',
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 0

            class TestFileNotFoundError:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'), name='zone'
                        ),
                    )

                    # ASSERT
                    with warns(EnergyUjNotFoundWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_not_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'), name='zone'
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 0

            class TestPermissionError:
                def test_raises_warning(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                            energy_uj_mode=0o000,
                        ),
                    )

                    # ASSERT
                    with warns(EnergyUjPermissionWarning, match=backend):
                        discover_power_telemetry_sensors(sys_path)

                def test_sensor_not_included(
                    self,
                    sys_path: Path,
                    mock_powercap_backend: MockPowercapBackend,
                    backend: str,
                    dir_name: str,
                    zone_prefix: str,
                    all_zones: list[PowercapZone],
                ):
                    # ARRANGE
                    mock_powercap_backend(
                        dir_name,
                        PowercapZone(
                            relative_path=Path(f'{zone_prefix}0'),
                            energy_uj=0,
                            name='zone',
                            energy_uj_mode=0o000,
                        ),
                    )

                    # ACT
                    sensors = discover_power_telemetry_sensors(sys_path)

                    # ASSERT
                    assert len(sensors.energy_sensors) == 0


class TestHwmon:
    """Tests related to the `hwmon` dir search."""

    def test_warns_if_not_found_and_powercap_exists(self, powercap_path: Path):
        # ARRANGE
        sys_path = powercap_path.parent.parent

        # ASSERT
        with warns(HwmonNotFoundWarning):
            discover_power_telemetry_sensors(sys_path)
