# powercap_paths = []
# powercap_metrics_joule = {}
#
# FOR path IN "/sys/class/powercap/intel-rapl/intel-rapl:*/":
#   powercap_paths.append(path)
#
# IF powercap_paths.length == 0:
#   FOR path IN "/sys/class/powercap/arm-scmi:*/":
#     powercap_paths.append(path)
#
# IF powercap_paths.length > 0:
#   FOR path IN powercap_paths:
#     powercap_metrics_joule[name from path] = energy_uj
#     FOR path in (path + path:*) as subpath:
#     powercap_metrics_joule[name from subpath] = energy_uj
#
# hwmon_metrics = {}
# FOR path in hwmon*:
#   IF (name in path) is ^(
#     coretemp
#     |peci_cputemp
#     |k8temp
#     |k10temp
#     |zenpower
#     |amd_energy
#     |fam15h_power
#     |via_cputemp
#     |macsmc.*
#     |apple_m1_hwmon
#     |scpi_sensors
#     |xgene_hwmon
#     |arm_big_little
#     |ibmpowernv
#     |occ
#     |aem
#     |loongson[23]_hwmon
#   )$:
#     hwmon_metrics[name] = name
#
#     FOR subpath in path:
#       IF subpath is (power.*_average)$:
#         hwmon_metrics[name].power_average = subpath.content
#       ELSE IF subpath is (power.*_input)$:
#         hwmon_metrics[name].power_input = subpath.content
#       ELSE IF subpath is (energy.*_input)$:
#         hwmon_metrics[name].energy_input = subpath.content
#
# 1. Check the power capping framework.
#    1. Check if `/sys/class/powercap/intel-rapl:*/` dirs exist.
#       - If positive, then the machine has Intel or AMD CPU(s). Then
#         parse the `energy_uj` files , saving the corresponding power
#         zones’ names to know which zone each number belongs to.
#       - If negative, check if `/sys/class/powercap/arm-scmi:*/` dirs
#         exist. This is the equivalent interface for ARM processors.
#         It works the same way as the RAPL interface.
#       - Besides the zones, parse `energy_uj` file contents in the
#         subzones as well, and cache the values similarly.
#    3. From the cached values, calculate the CPU power consumption
#       metrics and save them in the returned `CpuStats` instance. It is
#       impossible to say which metrics the user is interested in, so
#       pick the most safe default (probably `package - uncore`, because
#       `core` does not equal `package - uncore`) and give the user the
#       right to choose any other possible representation as he or she
#       wishes.
# 2. Check HWMon.
#    - Find the `/sys/class/hwmon/hwmon*` dir(s) that correspond(s) to the
#      CPU(s). There, check if a `power*_input` or `power*_average` file
#      exists. If positive, use it.
# 3. Read the RAPL values directly from the MSRs via the `msr` module.
#    - NOT IMPLEMENTED! It’s just a reminder that it is possible if
#      necessary. But it would require either root permissions or the
#      `CAP_SYS_RAWIO` capability.

import warnings
from pathlib import Path

from pytop.backend.cpu.power_telemetry._create_and_append_sensor import (
    create_and_append_powercap_energy_sensor,
)
from pytop.backend.cpu.power_telemetry.exceptions import (
    PowercapInterfaceNotFoundWarning,
    PowercapNotFoundWarning,
)
from pytop.backend.cpu.power_telemetry.sensors import (
    EnergySensor,
    PowerSensor,
    PowerTelemetrySensors,
)


def discover_power_telemetry_sensors(
    sys_path: Path = Path('/sys'),
) -> PowerTelemetrySensors:
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
    else:
        warnings.warn(PowercapNotFoundWarning(powercap_path))

    return PowerTelemetrySensors(energy_sensors, power_sensors)
