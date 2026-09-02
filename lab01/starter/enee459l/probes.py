"""Probes — read what the machine says about itself.

STUDENT STARTER. Implement every function marked with a TODO below.

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

# ---------------------------------------------------------------------------
# Small helpers. These are given to students; the exercise is the probes.
# ---------------------------------------------------------------------------


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


def unknown(source: str, why: str) -> dict[str, Any]:
    """The value this lab returns when it cannot determine something.

    Note what this is not: it is not None threaded through the report, and it
    is not a plausible default. It is an explicit record that the probe ran and
    failed, carrying the reason. Assignment 1's rubric gives credit for these.
    """
    return {"value": None, "source": source, "status": "unknown", "detail": why}


# ---------------------------------------------------------------------------
# YOUR WORK STARTS HERE.
#
# Eight functions below raise NotImplementedError. Replace each body. Run
#
#     python3 -m pytest tests/test_public.py -v
#
# as you go — the tests run against fake machines in tests/fixtures/, so they
# work on your laptop before you ever touch a board.
#
# Two rules the tests enforce, and the graders enforce again:
#
#   1. Read only from `root`. Never hardcode "/". A probe that ignores its root
#      argument cannot be tested, and a measurement nobody can test is a
#      measurement nobody should believe.
#   2. When you cannot determine something, return unknown(source, why). Never
#      return 0, "", or a plausible default. `unknown` is a correct answer and
#      it is marked as one. A fabricated 0 is not, and it is marked as that.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The probes.
# ---------------------------------------------------------------------------


def probe_module_model(root: Path = Path("/")) -> dict[str, Any]:
    """Which board is this?

    The device tree model string is the most trustworthy identity on a Jetson —
    it comes from the hardware description the bootloader handed the kernel,
    not from anything installed afterwards.
    """

    # TODO: implement this probe.
    # Read /proc/device-tree/model with the read_text helper.
    # That node is NUL-terminated; read_text already strips it for you.
    # Return {'value': <the string>, 'source': src, 'status': 'ok'},
    # or unknown(src, <why>) if the node is not there.
    src = "/proc/device-tree/model"
    raise NotImplementedError("probes.probe_module_model")


def probe_memory_total_kb(root: Path = Path("/")) -> dict[str, Any]:
    """How much memory is there, in kB, as the kernel counts it?

    This will read a little under 8 GB on an 8 GB board. That gap is not a
    fault: the carveout for the GPU and other hardware is taken before Linux
    ever sees the pool. Students are expected to notice and to explain it in
    their report rather than round it up.
    """

    # TODO: implement this probe.
    # Read /proc/meminfo and find the MemTotal line.
    # Anchor your match to the start of a line, and return an int of kB,
    # not the string and not the whole line.
    src = "/proc/meminfo"
    raise NotImplementedError("probes.probe_memory_total_kb")


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

    # TODO: implement this probe.
    # Read /proc/mounts. Each line is: device mountpoint fstype options ...
    # Find the line whose mountpoint is exactly '/' — it is not always first,
    # and '/var' is not '/'.
    # Return 'value' (the device) and also 'kind', one of:
    #     'nvme'               device starts with /dev/nvme
    #     'removable_or_sata'  device starts with /dev/mmcblk or /dev/sd
    #     'other'              anything else, e.g. a tmpfs or NFS root
    # The 'kind' field is what the verdict in report.py branches on.
    src = "/proc/mounts"
    raise NotImplementedError("probes.probe_root_source")


def probe_nvme_present(root: Path = Path("/")) -> dict[str, Any]:
    """Is there an NVMe device visible as a block device at all?

    Deliberately separate from probe_root_source. A machine can have an NVMe
    fitted and still boot from the SD card, and telling those two states apart
    is what lets the troubleshooting tree in the lab guide send a student to
    the right branch.
    """

    # TODO: implement this probe.
    # Does <root>/sys/block/nvme0n1 exist?
    # This must NOT look at what the root filesystem is mounted from. A board
    # can have an NVMe fitted and still boot from the SD card, and telling
    # those two apart is the entire point of the lab.
    # Return 'value' as a bool, plus 'model' from
    # /sys/block/nvme0n1/device/model if you can read it, else None.
    src = "/sys/block/nvme0n1"
    raise NotImplementedError("probes.probe_nvme_present")


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


def _parse_link_line(line: str) -> dict[str, Any]:

    # TODO: implement this helper.
    # Pull the speed and width out of one LnkSta: or LnkCap: line.
    # _SPEED_RE and _WIDTH_RE above already match them.
    # Return {'raw', 'gts', 'width', 'gen'} — map GT/s to a generation with
    # _GEN_BY_GTS, and use None for anything the line does not state.
    raise NotImplementedError("probes._parse_link_line")


def probe_pcie_link(root: Path = Path("/"), lspci_output: str | None = None) -> dict[str, Any]:
    """What did the PCIe link negotiate, and what was it capable of?

    Two numbers, not one. The gap between them is the lab's worked example of
    spec sheet against measured reality: a Gen4 drive in a Gen3 slot advertises
    16 GT/s and settles at 8 GT/s, and a student who reports only the second
    number has recorded a fact without recording what it means.

    `lspci_output` exists so the tests can drive this without root or hardware.
    In normal use it is None and the probe shells out.
    """

    # TODO: implement this probe.
    # Use `text` below — it is either the lspci output handed in by a test or
    # the real thing. If it is empty, that is an unknown, not a failure.
    # Find the LnkSta: line and the LnkCap: line and parse BOTH with
    # _parse_link_line. Two numbers, kept separate:
    #     negotiated  what the link actually came up at   (LnkSta)
    #     capability  what the drive could have done      (LnkCap)
    # Without sudo, lspci often prints no LnkCap at all. Report that as
    # capability=None. Do not fill it in from LnkSta.
    # If both generations are known, add an 'interpretation' string saying
    # either that the drive is capped by the slot, or that it is running at
    # full capability.
    src = "lspci -vv"
    text = lspci_output if lspci_output is not None else run(["lspci", "-vv"])
    raise NotImplementedError("probes.probe_pcie_link")


def probe_thermal_zones(root: Path = Path("/")) -> dict[str, Any]:
    """Every thermal zone the kernel exposes, in degrees C.

    Sysfs reports millidegrees. The division by 1000 is the entire trap: a
    report claiming the board idles at 43,000 degrees has been submitted more
    than once, and it is a good, cheap lesson in reading units before reading
    numbers.
    """

    # TODO: implement this probe.
    # Walk <root>/sys/class/thermal/thermal_zone*/.
    # Each zone has a 'temp' file in MILLIDEGREES and a 'type' file.
    # Divide by 1000. A board does not idle at 43,000 degrees.
    # Return 'zones' (a list of {'zone', 'type', 'temp_c'}) and 'value' as the
    # hottest zone. A zone can legitimately read below zero.
    # Directory absent, or present with nothing readable in it, are both
    # unknown — and neither of them is 0.0.
    src = "/sys/class/thermal/thermal_zone*/temp"
    base = Path(root) / "sys/class/thermal"
    raise NotImplementedError("probes.probe_thermal_zones")


def probe_power_mode(root: Path = Path("/"), nvpmodel_output: str | None = None) -> dict[str, Any]:
    """Which nvpmodel power mode is active?

    Recorded on every artifact this course produces. Lecture 01 slide 24 is
    the argument for why: two students reporting different throughput for the
    same model are usually reporting different power modes, and without this
    field there is no way to find that out after the fact.
    """

    # TODO: implement this probe.
    # Use `text` below, as with the PCIe probe.
    # Parse the mode name out of the 'NV Power Mode: <name>' line, and the
    # numeric mode id off the line by itself if there is one.
    # nvpmodel does not exist off a Jetson. That is expected, and it is an
    # unknown with a reason, not a crash.
    src = "nvpmodel -q"
    text = nvpmodel_output if nvpmodel_output is not None else run(["nvpmodel", "-q"])
    raise NotImplementedError("probes.probe_power_mode")
