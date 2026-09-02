# Lab 01 — What is this machine, and how do you know?

**Platform health: probing NVMe boot, temperature, link speed, and memory—with evidence.**

## The Question

A Jetson can have an NVMe drive fitted, visible to the kernel, and completely unused, because the operating system boots from the SD card. It works. It passes casual inspection. It also runs every benchmark this semester against storage an order of magnitude slower than the drive sitting unused in its slot, and every number it produces is quietly, unreproducibly wrong. Can you tell the two apart?

## What You Will Build

Seven standalone probes reading sysfs, /proc, and CLI tools:

- **`probe_module_model`**: The CPU module name from `/proc/device-tree/model`.
- **`probe_memory_total_kb`**: Total RAM in kB (always less than 8 GB on Orin Nano).
- **`probe_root_source`**: Which device the root filesystem boots from (NVMe, SD, or other).
- **`probe_nvme_present`**: Whether an NVMe drive exists in `/sys/block/nvme0n1` (fitted ≠ booted-from).
- **`probe_pcie_link`**: Two PCIe numbers—what the link *can* do (capability) and what it *did* do (negotiated).
- **`probe_thermal_zones`**: All thermal zones in millidegrees Celsius, divided by 1000 to get degrees.
- **`probe_power_mode`**: Current NVIDIA power mode (MAXN SUPER, 15W, etc.) from `nvpmodel`.

All reads use a `root` parameter so tests can inject fake filesystems. When you cannot read something, you return `unknown(source, why)`, not a plausible default.

## How to Run

```bash
cd labs/lab01/solution

# Install test dependencies
pip install pytest

# Build fake machines for testing
make fixtures

# Run public tests
make test

# Run all tests
make test-all

# Generate the report on the board
python3 system_report.py --device-id jetson-07 -o system_report.json
```

The report validates against a JSON schema. Check it before submitting:

```bash
python3 -c "import json, sys; from enee459l import schema; print(schema.validate(json.load(open('system_report.json'))) or 'valid')"
```

## Exit Codes

- `0`: all verdicts passed
- `1`: a verdict failed (the machine is misconfigured)
- `2`: a verdict is unknown (missing a measurement tool like `lspci` or `nvpmodel`)
- `3`: schema validation failed (code error)

## The Two Questions This Lab Answers

**Is the board booting from NVMe or SD?** The `probe_root_source` verdict `boots_from_nvme` checks this. If it says your board boots from `/dev/mmcblk0p1`, the semester's benchmarks are running against the slow card, not the fast drive.

**Did the PCIe link negotiate to Gen3 or Gen4?** The drive's box says Gen4. The slot is Gen3 ×4. `probe_pcie_link` returns both the link's capability and what it actually negotiated. The gap is the lesson: a component's spec sheet is an upper bound, not a statement about your system.

## Verdicts

1. **the_module_exists**: The CPU module name is readable.
2. **the_memory_matches_the_label**: Total memory ≥ 6 GB (Orin Nano should report ~7.6 GB).
3. **boots_from_nvme**: Root filesystem is on `/dev/nvme0n1`, not `/dev/mmcblk0p1`.
4. **nvme_is_fitted**: An NVMe drive exists and reports a model.
5. **the_link_is_negotiated**: Both PCIe capability and negotiated speed are known.
6. **the_link_is_gen3**: The link negotiated at Gen3, not higher (due to board wiring).
7. **the_thermal_zones_are_readable**: At least one thermal zone reports a temperature.
8. **the_power_mode_is_set**: Power mode is readable and is MAXN SUPER (or an expected lower mode).
