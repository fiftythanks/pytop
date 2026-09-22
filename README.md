# Pytop

> **Status: Prototype & Systems Exploration (Archived)**
>
> Pytop is an experimental, zero-dependency Python 3.13 backend prototype built to explore low-level Linux kernel interfaces (`/proc` and `/sys`) from scratch. It gathers process and CPU power telemetry without third-party libraries such as `psutil`.
>
> Having successfully built the core telemetry parsers and verified them with an extensive test suite, development concluded without implementing a TUI layer. High-frequency polling and dynamic string parsing over the Linux virtual filesystem highlighted the inherent runtime overhead of Python for low-level systems monitoring, prompting a pivot towards systems programming in Rust.

---

## Overview & Philosophy

* **Zero External Dependencies:** Implemented exclusively with the Python 3.13+ Standard Library (`pathlib`, `dataclasses`, `time`, `warnings`, `pwd`, `os` and `signal`). No `psutil` and no C extensions.
* **Direct Kernel Interfacing:** All telemetry is derived by parsing the Linux virtual filesystem (`/proc` and `/sys`) and invoking standard POSIX system calls.
* **Defensive Failure Handling:** Virtual filesystem files can vanish between reads, unprivileged users encounter permission boundaries and hardware sensors occasionally emit empty or corrupted values. The engine isolates errors, emits granular custom warnings and falls back to `None` instead of raising unhandled exceptions.

---

## Core Architecture

### 1. Process Telemetry (`pytop.backend.proc`)

The process monitor crawls `/proc` and parses process metadata:

* **Instantaneous CPU Utilisation:** Derives CPU usage per process across sampling intervals by computing elapsed `USER_HZ` ticks against system-wide tick deltas from `/proc/stat`. Supports IRIX mode, scaling calculations across available CPU cores:
  $$\text{utilisation} = \left(\frac{\Delta\text{process ticks}}{\Delta\text{cpu ticks}}\right) \times 100 \times \text{cores}$$
* **Process Lifecycles & State:** Parses `/proc/[pid]/status`, `/proc/[pid]/cmdline` and `/proc/[pid]/io` for memory footprint (`VmRSS`), process state flags (`State`), thread counts, I/O read/write byte counts and process uptime using `os.sysconf('SC_CLK_TCK')`.
* **User Resolution:** Maps effective user IDs (`euid`) to system usernames via `pwd.getpwuid` with safe fallback to raw numerical IDs.

### 2. Process Actions (`pytop.backend.proc.actions`)

Provides POSIX process management primitives wrapped in typed exceptions:

* **Priority Scheduling (`renice`):** Adjusts process nice values ($-20$ to $19$) via `os.setpriority(os.PRIO_PROCESS, pid, priority)`.
* **Signal Dispatch (`send_signal`):** Dispatches standard POSIX signals (1–31) to target processes via `os.kill(pid, sig)`.
* **Typed Error Wrappers:** Translates `PermissionError` and `ProcessLookupError` into distinct project exceptions (`RenicePermissionError`, `SignalPermissionError` and `ProcActionProcessLookupError`).

### 3. CPU & Power Telemetry (`pytop.backend.cpu`)

Monitors overall system utilisation and hardware energy counters:

* **Tick Mathematics:** Parses `/proc/stat` to accumulate tick distributions (`user`, `nice`, `system`, `idle`, `iowait`, `irq`, `softirq` and `steal`), calculating overall CPU utilisation percentages across polling intervals.
* **System Metrics:** Parses `/proc/uptime`, `/proc/loadavg` (1-, 5- and 15-minute load averages) and `/proc/cpuinfo` (model designation).
* **Powercap Energy Telemetry:** Discovers and traverses the Linux Powercap hierarchy (`/sys/class/powercap`), supporting Intel RAPL and ARM SCMI topologies (packages and subzones). Because energy is reported as cumulative microjoules (`energy_uj`), the backend maintains a state machine measuring delta microjoules against high-resolution monotonic timestamps (`time.monotonic_ns()`) to calculate real-time wattage:
  $$P\text{ (Watts)} = \frac{\Delta E\text{ (Joules)}}{\Delta t\text{ (Seconds)}}$$

---

## Quality Infrastructure & Testing

The repository maintains strict typing, automated formatting and comprehensive test coverage:

* **Test Suite:** 460+ automated tests executed with `pytest` (exceeding 3,600 lines of test code).
* **VFS Simulation:** Unit tests utilise pytest's `tmp_path` fixture to construct mock `/proc` and `/sys` directory trees, verifying behaviour against edge cases including missing entries, empty strings, permission denials and corrupted sensor data.
* **Custom Warning Assertions:** Pytest runs with warnings configured as errors (`filterwarnings = ["error"]`). Tests explicitly verify that non-fatal kernel conditions emit the exact expected warning subclasses (e.g. `ProcStatPermissionWarning`, `ZoneNameNotFoundWarning`, `PowerTelemetrySensorValueWarning`).
* **Subprocess Integration Tests:** Integration suites in `tests/backend/integration/test_proc.py` spawn real child processes to validate `renice` priority adjustments and signal propagation (`SIGTERM`), with strict teardown fixtures (`terminate` $\rightarrow$ `wait` $\rightarrow$ `kill` $\rightarrow$ `wait`) ensuring clean process cleanup.
* **Type Safety:** 100% strict type checking with `basedpyright` in strict mode with zero errors and zero warnings.
* **Code Standards:** Linted and formatted using `ruff` adhering to strict PEP 8 conventions.

---

## Reflections & Pivot

Building Pytop provided valuable hands-on experience with Linux kernel interfaces, process management and hardware telemetry. However, exploring high-frequency sampling over `/sys` and `/proc` in Python revealed fundamental limitations:

1. **Virtual Filesystem Overhead:** Reading kernel VFS nodes requires frequent filesystem calls where the kernel serialises internal structures into text, which Python must parse and allocate dynamically into strings on every polling cycle.
2. **Low-Level Systems Requirements:** Hardware-level telemetry and high-frequency profiling benefit significantly from direct binary structures, unbuffered file descriptors and predictable memory footprints without garbage collection pauses.

These insights led to concluding this exploratory prototype and shifting focus to systems programming in Rust.
