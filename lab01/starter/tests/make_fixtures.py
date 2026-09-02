#!/usr/bin/env python3
"""Build the fake machine trees the test suite probes against.

Two machines, and the difference between them is the failure this lab exists to
teach:

    nvme_good/  a correctly imaged unit — root on NVMe, Gen4 drive negotiating
                Gen3 because that is what the carrier board is wired for
    sd_boot/    the silent failure — NVMe fitted and visible, root still on the
                SD card, everything apparently fine

A third tree, `bare/`, has almost nothing readable. It exists so that the
"unknown" path is tested too: probes must degrade into a recorded reason rather
than an exception or a plausible default.

Run from either tree:  python3 tests/make_fixtures.py
Regenerating is safe; it overwrites.
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"

MEMINFO_8GB = """\
MemTotal:        7650000 kB
MemFree:         5432100 kB
MemAvailable:    6120000 kB
Buffers:           89000 kB
Cached:           980000 kB
SwapTotal:       3825000 kB
SwapFree:        3825000 kB
"""

MEMINFO_TINY = """\
MemTotal:        2048000 kB
MemFree:         1000000 kB
"""

MOUNTS_NVME = """\
/dev/nvme0n1p1 / ext4 rw,relatime 0 0
none /proc proc rw,nosuid,nodev,noexec,relatime 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
tmpfs /run tmpfs rw,nosuid,nodev,size=765000k 0 0
"""

MOUNTS_SD = """\
/dev/mmcblk0p1 / ext4 rw,relatime 0 0
none /proc proc rw,nosuid,nodev,noexec,relatime 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
"""

# A Gen4 drive in the devkit's Gen3-wired M.2 Key-M slot. Capability says
# 16GT/s, status says 8GT/s. Both lines are real-shaped lspci -vv output.
LSPCI_GEN4_IN_GEN3 = """\
0001:01:00.0 Non-Volatile memory controller: Sandisk Corp WD Black SN770 (rev 01)
\tSubsystem: Sandisk Corp WD Black SN770
\tCapabilities: [80] Express (v2) Endpoint, MSI 00
\t\tLnkCap:\tPort #0, Speed 16GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
\t\tLnkCtl:\tASPM L1 Enabled; RCB 64 bytes, Disabled- CommClk+
\t\tLnkSta:\tSpeed 8GT/s, Width x4, TrErr- Train- SlotClk+ DLActive- BWMgmt- ABWMgmt-
\tKernel driver in use: nvme
"""

# A drive running at its full capability — used to check that the probe does
# not report a shortfall where there is none.
LSPCI_GEN3_MATCHED = """\
0001:01:00.0 Non-Volatile memory controller: Generic NVMe (rev 01)
\t\tLnkCap:\tPort #0, Speed 8GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
\t\tLnkSta:\tSpeed 8GT/s, Width x4, TrErr- Train- SlotClk+ DLActive- BWMgmt- ABWMgmt-
"""

NVPMODEL_MAXN = """\
NV Power Mode: MAXN_SUPER
2
"""

NVPMODEL_15W = """\
NV Power Mode: 15W
0
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def reset(root: Path) -> None:
    """Clear a machine tree if we are allowed to, and say so if we are not.

    Some filesystems this course is authored and graded on — network shares,
    container mounts, a few CI sandboxes — permit creating and overwriting files
    but not unlinking them. Since every fixture file below is written
    unconditionally, an overwrite is enough to make the tree correct, and dying
    here would stop the tests from running at all on those machines.

    The one case an overwrite does not cover is a file that used to be part of a
    machine and no longer is. That is worth a warning rather than silence,
    because it is exactly the kind of leftover that makes a test pass for a
    reason nobody intended.
    """
    if not root.exists():
        return
    try:
        shutil.rmtree(root)
    except (PermissionError, OSError) as e:
        print(f"  note: could not clear {root.name} ({e.strerror}); overwriting in place.")
        print(f"        if {root.name} was built by an older version of this script,")
        print(f"        delete tests/fixtures/ by hand before trusting a result.")


def build_machine(name: str, *, meminfo: str, mounts: str, nvme: bool,
                  thermal: dict[str, int] | None, model: str | None) -> None:
    root = FIX / name
    reset(root)
    write(root / "proc/meminfo", meminfo)
    write(root / "proc/mounts", mounts)
    if model is not None:
        # The real node is NUL-terminated; probes must cope with that.
        write(root / "proc/device-tree/model", model + "\x00")
    if nvme:
        write(root / "sys/block/nvme0n1/device/model", "WD Black SN770 1TB   \n")
        write(root / "sys/block/nvme0n1/size", "1953525168\n")
    if thermal:
        for i, (typ, milli) in enumerate(thermal.items()):
            write(root / f"sys/class/thermal/thermal_zone{i}/type", typ + "\n")
            write(root / f"sys/class/thermal/thermal_zone{i}/temp", str(milli) + "\n")


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)

    build_machine(
        "nvme_good",
        meminfo=MEMINFO_8GB,
        mounts=MOUNTS_NVME,
        nvme=True,
        thermal={"cpu-thermal": 42500, "gpu-thermal": 41000, "tj-thermal": 43250},
        model="NVIDIA Jetson Orin Nano Developer Kit",
    )

    build_machine(
        "sd_boot",
        meminfo=MEMINFO_8GB,
        mounts=MOUNTS_SD,
        nvme=True,  # fitted and visible — and still not booted from
        thermal={"cpu-thermal": 44000, "gpu-thermal": 42000, "tj-thermal": 45000},
        model="NVIDIA Jetson Orin Nano Developer Kit",
    )

    build_machine(
        "bare",
        meminfo=MEMINFO_TINY,
        mounts="tmpfs / tmpfs rw 0 0\n",
        nvme=False,
        thermal=None,
        model=None,
    )

    # lspci captures live beside the trees rather than inside them, because
    # lspci is a command and not a file, and pretending otherwise would teach
    # the wrong shape.
    write(FIX / "lspci_gen4_in_gen3.txt", LSPCI_GEN4_IN_GEN3)
    write(FIX / "lspci_gen3_matched.txt", LSPCI_GEN3_MATCHED)
    write(FIX / "nvpmodel_maxn.txt", NVPMODEL_MAXN)
    write(FIX / "nvpmodel_15w.txt", NVPMODEL_15W)

    print(f"fixtures written to {FIX}")
    for p in sorted(FIX.iterdir()):
        print("  ", p.name)


if __name__ == "__main__":
    main()
