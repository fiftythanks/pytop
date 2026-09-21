import warnings
from pathlib import Path

from pytop.backend.cpu.power_telemetry._create_and_append_sensor import (
    create_and_append_powercap_energy_sensor,
)
from pytop.backend.cpu.power_telemetry.exceptions import (
    HwmonNotFoundWarning,
    PowercapInterfaceNotFoundWarning,
    PowercapNotFoundWarning,
    PowerTelemetryNotFoundWarning,
)
from pytop.backend.cpu.power_telemetry.sensors import (
    EnergySensor,
    PowerSensor,
    PowerTelemetrySensors,
)


def discover_power_telemetry_sensors(
    sys_path: Path = Path('/sys'),
) -> PowerTelemetrySensors:
    """Search the system for power telemetry sensors.

    When searching, it checks each sensor’s power/energy consumption value. If
    the value is incorrect, it doesn’t include the sensor into the resulting
    list. Examples of incorrect values are not a number or a negative number.

    Search strategy:

        First it goes through the `/sys/class/powercap/intel-rapl/` directory. If
        no sensors found there or the directory doesn’t exist, it checks the
        `/sys/class/powercap/arm-scmi/` directory.

        (NOT IMPLEMENTED) Regardless of the outcome, it then proceeds to search the
        `/sys/class/hwmon/` directory for any sensors present there.

    All found sensors are returned as `PowerTelemetrySensors` afterwards.
    """

    energy_sensors: list[EnergySensor] = []
    power_sensors: list[PowerSensor] = []

    # -------------------------------------------------------------------------
    # POWERCAP
    # -------------------------------------------------------------------------
    powercap_path = sys_path / 'class' / 'powercap'

    if powercap_path.exists():
        intel_rapl_path = powercap_path / 'intel-rapl'
        arm_scmi_path = powercap_path / 'arm-scmi'

        if intel_rapl_path.exists():
            backend = 'Intel RAPL'

            for path in intel_rapl_path.iterdir():
                if path.name.find('intel-rapl:') != -1:
                    create_and_append_powercap_energy_sensor(
                        backend, path, energy_sensors
                    )

                    for subzone_path in path.iterdir():
                        if subzone_path.name.find(f'{path.name}:') != -1:
                            create_and_append_powercap_energy_sensor(
                                backend, subzone_path, energy_sensors
                            )

        elif arm_scmi_path.exists():
            backend = 'ARM SCMI'

            for path in arm_scmi_path.iterdir():
                if path.name.find('arm-scmi:') != -1:
                    create_and_append_powercap_energy_sensor(
                        backend, path, energy_sensors
                    )

                    for subzone_path in path.iterdir():
                        if subzone_path.name.find(f'{path.name}:') != -1:
                            create_and_append_powercap_energy_sensor(
                                backend, subzone_path, energy_sensors
                            )
        else:
            warnings.warn(PowercapInterfaceNotFoundWarning(powercap_path))

    # -------------------------------------------------------------------------
    # HWMON
    # -------------------------------------------------------------------------
    # TODO: Implement later. Virtually all modern machines will have powercap.
    hwmon_path = sys_path / 'class' / 'hwmon'

    if hwmon_path.exists():
        if not powercap_path.exists():
            warnings.warn(PowercapNotFoundWarning(powercap_path))

    elif powercap_path.exists():
        warnings.warn(HwmonNotFoundWarning(hwmon_path))
    else:
        warnings.warn(PowerTelemetryNotFoundWarning(sys_path))

    # -------------------------------------------------------------------------
    # DIRECT MSR READS
    # -------------------------------------------------------------------------
    # NOTE: I’m leaving it here just so we remember this option exists. But
    # since it will not be needed almost certainly, I don’t think it is wise to
    # spend time implementing it.

    return PowerTelemetrySensors(energy_sensors, power_sensors)
