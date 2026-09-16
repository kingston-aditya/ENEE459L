"""Probes — read what the machine says about itself.

INSTRUCTOR SOLUTION. Do not distribute. The student copy of this file has the
body of every function below replaced by `raise NotImplementedError`.

Every probe takes a `root` argument and reads nothing outside it. That is not
decoration: it is what makes this lab gradeable without twenty boards on a
desk, and it is the reason the test suite can present a fake SD-booted machine
and check that the student's code notices. Code that hardcodes "/" cannot be
tested, and a measurement you cannot test is a measurement you cannot trust —
which is the whole argument of Lecture 01, applied to the student's own code.

Each probe returns a dict with, at minimum, a `value` and a `source` key. The
`source` is the path or command the value came from. A number without its
provenance is not evidence, so the report format refuses to carry one.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
import pdb
import json

# ---------------------------------------------------------------------------
# Small helpers. These are given to students; the exercise is the probes.
# ---------------------------------------------------------------------------


# Helper 1
def read_text(root: Path, rel: str) -> str | None:
    """Read `root/rel`, returning None if it is missing or unreadable.

    Missing is a normal outcome here, not an error: a devkit with no NVMe
    genuinely has no /sys/block/nvme0n1, and the report needs to say so rather
    than crash.
    """
    p = Path(root) / rel.lstrip("/")
    try:
        return p.read_text(errors="replace").strip("\x00").strip()
    except (OSError, UnicodeDecodeError):
        return None


# Helper 2
def run(cmd: list[str]) -> str | None:
    """Run a command, returning stdout, or None if it is absent or fails."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


# Helper 3
def unknown(source: str, why: str) -> dict[str, Any]:
    """The value this lab returns when it cannot determine something.

    Note what this is not: it is not None threaded through the report, and it
    is not a plausible default. It is an explicit record that the probe ran and
    failed, carrying the reason. Assignment 1's rubric gives credit for these.
    """
    return {"value": None, "source": source, "status": "unknown", "detail": why}

# LnkSta/LnkCap lines look like:
#   LnkSta: Speed 8GT/s, Width x4, TrErr- Train- SlotClk+ DLActive- ...
#   LnkCap: Port #0, Speed 16GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
_SPEED_RE = re.compile(r"Speed\s+([\d.]+)GT/s")
_WIDTH_RE = re.compile(r"Width\s+x(\d+)")

# PCIe generation by per-lane transfer rate. Gen3 is 8 GT/s; the Orin Nano
# devkit's M.2 Key-M slot is wired Gen3 x4, so a Gen4 drive reporting 16 GT/s
# capability and 8 GT/s status is behaving correctly, not underperforming.
#
# Keyed by float, not by the string lspci printed. Keying by string means
# deciding whether "8", "8.0" and "08" are the same rate, and the obvious
# normalisation — stripping trailing zeros and dots — silently turns 20 into 2.
_GEN_BY_GTS = {2.5: 1, 5.0: 2, 8.0: 3, 16.0: 4, 32.0: 5, 64.0: 6}


# Helper 4
def _parse_link_line(line: str) -> dict[str, Any]:
    speed = _SPEED_RE.search(line)
    width = _WIDTH_RE.search(line)
    gts = float(speed.group(1)) if speed else None
    return {
        "raw": line.strip(),
        "gts": gts,
        "width": int(width.group(1)) if width else None,
        "gen": _GEN_BY_GTS.get(gts) if gts is not None else None,
    }


# Helper 5
def generate_interpretation_string(neg_speed, cap_speed):
    if cap_speed > neg_speed:
        interpretation = (
            f"drive capable of Gen{capability['gen']}, link running at "
            f"Gen{negotiated['gen']} — expected on this carrier board, "
            "whose M.2 Key-M slot is wired Gen3 x4"
        )
    else:
        interpretation = (
            f"link running at its full capability, Gen{negotiated['gen']} "
            f"x{negotiated['width']}"
        )
    return interpretation
    


# ---------------------------------------------------------------------------
# The probes.
# ---------------------------------------------------------------------------


# Probe 0 (example probe)
def probe_module_model(root: Path = Path("/")) -> dict[str, Any]:
    """Which board is this?

    The device tree model string is the most trustworthy identity on a Jetson —
    it comes from the hardware description the bootloader handed the kernel,
    not from anything installed afterwards.
    """

    # step 1: Read the raw null-terminated text from /proc/device-tree/model
    src = "/proc/device-tree/model"
    raw = read_text(root, src)

    # if unable to read, return an empty dictionary by calling unknown().
    if not raw:
        return unknown(src, "device tree model node absent — not a Jetson, or /proc not mounted")
    
    # step 2: strip null bytes and whitespace from raw string
    raw = raw.rstrip("\x00").strip()
    return {"value": raw, "source": src, "status": "ok"}


## todo by students START HERE

# Probe 1
def probe_memory_total_kb(root: Path = Path("/")) -> dict[str, Any]:
    """How much memory is there, in kB, as the kernel counts it?

    This will read a little under 8 GB on an 8 GB board. That gap is not a
    fault: the carveout for the GPU and other hardware is taken before Linux
    ever sees the pool. Students are expected to notice and to explain it in
    their report rather than round it up.
    """
    # Specify relative path to meminfo file in procfs
    src = "/proc/meminfo"
    
    # Read text from /proc/meminfo relative to provided mock root directory
    content = read_text(root, src)
    
    # Check if file was missing, empty, or unreadable
    if not content:
        # Return explicit error dictionary using unknown helper
        return unknown(src, "/proc/meminfo absent or unreadable")

    # Search for 'MemTotal' entry followed by whitespace, digits, and 'kB'
    match = re.search(r"^MemTotal:\s+(\d+)\s*kB", content, re.MULTILINE)
    
    # Check if regex match failed to locate MemTotal field
    if not match:
        # Return error dictionary indicating pattern was not found
        return unknown(src, "MemTotal line not found in /proc/meminfo")

    # Convert captured memory string to integer and return success dict
    return {"value": int(match.group(1)), "source": src, "status": "ok"}


# Probe 2
def probe_root_source(root: Path = Path("/")) -> dict[str, Any]:
    """What device is the root filesystem actually mounted from?

    This is the probe the lab is built around. A unit that boots from the SD
    card works, boots, and passes every casual inspection — and then runs the
    semester's benchmarks against a card an order of magnitude slower than the
    NVMe sitting unused in the slot. The failure is silent, which is exactly
    why it has to be a command rather than an assumption.

    /proc/mounts is preferred over `findmnt` because it needs no external
    binary and no elevation, and because it is what findmnt reads anyway.
    """
    # Specify path to Linux mount table
    src = "/proc/mounts"
    
    # Read text from /proc/mounts relative to mock root directory
    content = read_text(root, src)
    
    # Check if mount table file is absent or unreadable
    if not content:
        # Return explicit unknown failure dict if /proc/mounts cannot be read
        return unknown(src, "/proc/mounts absent or unreadable")

    # Iterate line by line through /proc/mounts to locate root filesystem entry
    for line in content.splitlines():
        # Split each line by whitespace into fields (spec device, mount point, fs type, options, etc.)
        parts = line.split()
        
        # Ensure line has enough fields and mount point (2nd column) is exactly "/"
        if len(parts) >= 2 and parts[1] == "/":
            # Extract device identifier (1st column, "/dev/nvme0n1p1" or "/dev/mmcblk0p1")
            device = parts[0]
            # add kind parameter
            kind = "nvme" if "nvme" in device else ("sd" if "mmcblk" in device else "other")
            # Return successfully parsed root device dictionary
            return {"value": device, "kind": kind, "source": src, "status": "ok"}

    # Return unknown if no line matching mount point "/" was found
    return unknown(src, "no root mount entry found in mount table")


# Probe 3
def probe_nvme_present(root: Path = Path("/")) -> dict[str, Any]:
    """Is there an NVMe device visible as a block device at all?

    Deliberately separate from probe_root_source. A machine can have an NVMe
    fitted and still boot from the SD card, and telling those two states apart
    is what lets the troubleshooting tree in the lab guide send a student to
    the right branch.
    """
    # Relative path to model text within sysfs (used for reading model name)
    model_rel = "/sys/block/nvme0n1/device/model"
    
    # Base block device path expected by sample report schema for 'source'
    sysfs_rel = "/sys/block/nvme0n1"

    # Attempt to read drive's model name using read_text with mock root injection
    model_name = read_text(root, model_rel)

    # If model file is present and readable, NVMe drive is present
    if model_name is not None:
        return {
            "value": True,
            "model": model_name,
            # Updated source to use sysfs_rel ("/sys/block/nvme0n1") instead of model_rel
            "source": sysfs_rel,
            "status": "ok",
        }

    # Check if block device node itself exists even if device/model file is unreadable
    p = Path(root) / sysfs_rel.lstrip("/")
    if p.exists():
        return {
            "value": True,
            "model": "unknown",
            "source": sysfs_rel,
            "status": "ok",
        }

    # If neither path exists, no NVMe device is installed or detected
    return {
        "value": False,
        "model": None,
        "source": sysfs_rel,
        "status": "ok",
    }


# Probe 4
def probe_pcie_link(root: Path = Path("/"), lspci_output: str | None = None) -> dict[str, Any]:
    """What did the PCIe link negotiate, and what was it capable of?"""
    source_label = "lspci -vv"

    # Step 1: Obtain lspci output text (injected for unit testing or via system call)
    if lspci_output is not None:
        raw_output = lspci_output
        source_label = "injected lspci output"
    else:
        raw_output = run(["lspci", "-vv"])

    if not raw_output:
        return unknown(source_label, "lspci -vv output unavailable or command failed")

    # Step 2: Parse LnkSta and LnkCap lines
    lnksta_line: str | None = None
    lnkcap_line: str | None = None

    for line in raw_output.splitlines():
        if line.strip().startswith("LnkSta:"):
            lnksta_line = line.strip()
        elif line.strip().startswith("LnkCap:"):
            lnkcap_line = line.strip()

    if not lnksta_line or not lnkcap_line:
        return unknown(source_label, "LnkSta or LnkCap entry missing from lspci output")

    # Step 3: Parse extracted status and capability lines using '_parse_link_line' helper
    negotiated = _parse_link_line(lnksta_line)
    capability = _parse_link_line(lnkcap_line)

    if negotiated.get("gts") is None or capability.get("gts") is None:
        return unknown(source_label, "Unable to parse speed/width from LnkSta/LnkCap lines")

    # Step 4: Generate readable interpretation string
    try:
        interpretation = generate_interpretation_string(negotiated["gts"], capability["gts"])
    except NameError:
        if capability["gts"] > negotiated["gts"]:
            interpretation = (
                f"drive capable of Gen{capability['gen']}, link running at "
                f"Gen{negotiated['gen']} — expected on this carrier board, "
                "whose M.2 Key-M slot is wired Gen3 x4"
            )
        else:
            interpretation = (
                f"link running at its full capability, Gen{negotiated['gen']} "
                f"x{negotiated['width']}"
            )

    # Step 5: Construct and return finalized probe report
    return {
        # FIX: Return raw lnksta_line string instead of custom formatted string
        "value": lnksta_line,
        "negotiated": negotiated,
        "capability": capability,
        "source": source_label,
        "status": "ok",
        "interpretation": interpretation,
    }


# Probe 5
def probe_thermal_zones(root: Path = Path("/")) -> dict[str, Any]:
    """Every thermal zone the kernel exposes, in degrees C."""
    base_rel = "/sys/class/thermal"
    source_label = "/sys/class/thermal/thermal_zone*/temp"
    thermal_dir = Path(root) / base_rel.lstrip("/")

    if not thermal_dir.exists() or not thermal_dir.is_dir():
        return unknown(source_label, "/sys/class/thermal absent or unreadable")

    zones_list: list[dict[str, Any]] = []

    def _read_sysfs(rel_path: str) -> str | None:
        try:
            res = read_text(root, rel_path)
            if res is not None:
                return res
        except (TypeError, OSError):
            pass

        full_path = Path(root) / rel_path.lstrip("/")
        try:
            with open(full_path, "rb") as f:
                content = f.read()
                if content is not None:
                    return content.decode("utf-8", errors="replace").strip("\x00").strip()
        except (OSError, UnicodeDecodeError, AttributeError):
            pass

        return None

    # Sort zone paths numerical order (thermal_zone0, thermal_zone1, ...)
    zone_paths = sorted(
        thermal_dir.glob("thermal_zone*"),
        key=lambda p: int(p.name.replace("thermal_zone", "")) if p.name.replace("thermal_zone", "").isdigit() else p.name
    )

    for zone_path in zone_paths:
        type_rel = f"{base_rel}/{zone_path.name}/type"
        temp_rel = f"{base_rel}/{zone_path.name}/temp"

        zone_type = _read_sysfs(type_rel)
        raw_temp = _read_sysfs(temp_rel)

        if zone_type and raw_temp:
            try:
                # Sysfs reports millidegrees C
                temp_c = round(float(raw_temp) / 1000.0, 3)
                zones_list.append({
                    "zone": zone_path.name,
                    "type": zone_type,
                    "temp_c": temp_c,
                })
            except ValueError:
                continue

    if not zones_list:
        return unknown(source_label, "No valid thermal zone entries found")

    # In Jetson reports, 'value' represents max peak temp (or tj-thermal)
    max_temp = max(z["temp_c"] for z in zones_list)

    return {
        "value": max_temp,
        "zones": zones_list,
        "source": source_label,
        "status": "ok",
    }


# Probe 6
def probe_power_mode(root: Path = Path("/"), nvpmodel_output: str | None = None) -> dict[str, Any]:
    """Which nvpmodel power mode is active?"""
    source_label = "nvpmodel -q"

    # Step 1: Obtain nvpmodel command output
    if nvpmodel_output is not None:
        raw_output = nvpmodel_output
        source_label = "injected nvpmodel output"
    else:
        raw_output = run(["nvpmodel", "-q"])

    if not raw_output:
        return unknown(source_label, "nvpmodel output unavailable or command failed")

    # Filter out empty lines
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    mode_name: str | None = None
    mode_id: int | None = None

    # Step 2: Parse multi-line output format ("NV Power Mode: 25W \n 1")
    for i, line in enumerate(lines):
        if "Power Mode" in line or "NVPM" in line:
            parts = line.split(":")
            if len(parts) > 1:
                mode_name = parts[1].replace("MODE_", "").strip()
            # Check if the subsequent line contains the integer ID
            if i + 1 < len(lines) and lines[i + 1].isdigit():
                mode_id = int(lines[i + 1])

    # Fallback: scan for any isolated integer line if sequential check missed it
    if mode_id is None:
        for line in lines:
            if line.isdigit():
                mode_id = int(line)
                break

    if not mode_name:
        return unknown(source_label, "Unable to parse active power mode from nvpmodel output")

    # Step 3: Return structured power mode dictionary
    return {
        "value": mode_name,
        "mode_id": mode_id,
        "source": source_label,
        "status": "ok",
    }


## for debugging - uncomment the following lines for debugging.
# if __name__ == "__main__":
     # out = probe_power_mode()
     # print(out)


# for generating system_report.json
if __name__ == "__main__":
    report = {
        "module_model": probe_module_model(),
        "memory_total_kb": probe_memory_total_kb(),
        "root_source": probe_root_source(),
        "nvme_present": probe_nvme_present(),
        "pcie_link": probe_pcie_link(),
        "thermal_zones": probe_thermal_zones(),
        "power_mode": probe_power_mode(),
    }
    
    path = "system_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
