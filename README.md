# Pytop

An experimental, pure-Python Linux system monitor built from scratch. Inspired by the layout and UI of [btop](https://github.com/aristocratos/btop).

## Goals & Philosophy
* **No External Dependencies:** Built using the Python 3.13+ Standard Library. No `psutil`, no C/C++ extensions.
* **Systems Programming Education:** The primary goal of this project is to understand the Linux kernel's interfaces (`/proc` and `/sys`) by manually parsing hardware telemetry, process states, and OS metrics.
* **Defensive Architecture:** The Linux virtual filesystem is a hostile environment. Files disappear, permissions change dynamically, and hardware sensors report corrupted data. This daemon is built to degrade gracefully rather than crash.

## Architecture & Implementation Details

### Data Gathering: Polling vs. Discovery
To maintain a low overhead footprint, the application separates metric collection into two phases:
1. **Discovery (Run Once):** At startup, the app crawls `/sys/class/powercap` to identify valid hardware sensors and topologies.
2. **Polling (Run Continuously):** The app retains the `pathlib.Path` references to the exact hardware files and reads them directly on a fixed interval, avoiding expensive, repetitive `stat()` syscalls.

### Power & Energy Telemetry (Intel RAPL & ARM SCMI)
Power consumption is calculated by reading the Linux Powercap framework. Because the kernel reports cumulative energy consumption in microjoules (`energy_uj`), the backend acts as a state machine. It captures the energy at $T_1$ and $T_2$, measures the elapsed time using `time.monotonic_ns()`, and calculates the real-time $\Delta$ wattage per CPU zone (`package`, `core`, `uncore` etc.).

### CPU Virtualization & Tick Math
Overall CPU usage is not reported as a percentage by the kernel. The backend calculates the delta of elapsed `USER_HZ` ticks parsed from `/proc/stat` (comparing the sum of `user`, `system`, and `idle` states between intervals) to compute the true instantaneous CPU utilization.

## Testing Strategy
The project enforces 100% strict type checking (`basedpyright`) and comprehensive unit testing (`pytest`).

* **Simulating the OS:** Tests utilize the `tmp_path` fixture to dynamically generate mock `/proc` and `/sys` virtual filesystems, allowing full simulation of missing files, permission errors, and corrupted hardware sensors.
* **Warnings as Errors:** Pytest is configured to treat all warnings as errors by default. Because the application handles OS edge cases by emitting custom Python `Warnings` (e.g., `ProcStatPermissionWarning`) instead of crashing, tests must explicitly assert that the correct warnings are fired under the correct failure conditions.
* **Zombie Process Annihilation:** Integration tests spawn real subprocesses to test signaling (`SIGTERM`, `SIGKILL`) and priority scheduling (`renice`). Pytest fixtures use strict `yield` and `finally` escalation blocks (`terminate` -> `wait` -> `kill` -> `wait`) to ensure the kernel process table is left completely sterile.

## Technical Debt & Roadmap
* **God Fixtures:** The initial unit tests for `create_process_monitor()` were written using a static "God Fixture" that generated 27 edge-case processes. This has been refactored in newer modules, but remains in the `proc` tests to save development time.
* **Hwmon Power Fallback:** Currently, power telemetry relies exclusively on the `powercap` framework (Intel RAPL / ARM SCMI), which covers ~95% of modern hardware. Parsing `/sys/class/hwmon` for legacy or niche power sensors is stubbed and planned for a future v1.x release.
* **MSR Fallback:** Currently, power telemetry relies on sysfs (`powercap`). Future updates could explore direct hardware interaction via `/dev/cpu/*/msr` (requiring `CAP_SYS_RAWIO`) as a fallback for unsupported architectures.
