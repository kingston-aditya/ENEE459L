"""Assemble probe output into the Lab 01 system report.

Provided complete in both the starter and the solution. Assembling a dict is
not the skill this lab is testing, and handing students a fixed report shape
is what makes twenty groups' reports diffable against each other.

The one design rule worth reading before you edit this: every value in the
report carries the source it came from. `verdicts` are derived, never typed in,
so that a report cannot claim a machine passed a check the probes never ran.
"""

from __future__ import annotations

import datetime as _dt
import platform
from pathlib import Path
from typing import Any

from . import probes

SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect(root: Path = Path("/"), device_id: str = "unknown") -> dict[str, Any]:
    """Run every probe and return the raw findings, without judgement."""
    return {
        "schema_version": SCHEMA_VERSION,
        "device_id": device_id,
        "hostname": platform.node(),
        "collected_at": _utc_now(),
        "probe_root": str(root),
        "findings": {
            "module_model": probes.probe_module_model(root),
            "memory_total_kb": probes.probe_memory_total_kb(root),
            "root_source": probes.probe_root_source(root),
            "nvme_present": probes.probe_nvme_present(root),
            "pcie_link": probes.probe_pcie_link(root),
            "thermal": probes.probe_thermal_zones(root),
            "power_mode": probes.probe_power_mode(root),
        },
    }


def verdicts(report: dict[str, Any]) -> dict[str, Any]:
    """Turn findings into pass/fail claims, each with the evidence attached.

    A verdict is a triple: the claim, whether the evidence supports it, and the
    evidence itself. Nothing here invents a value — if a probe came back
    unknown, the verdict is `unknown` too, not `fail`. The distinction matters
    at the bench: `fail` means go fix the machine, `unknown` means go fix your
    measurement.
    """
    f = report["findings"]
    out: dict[str, Any] = {}

    root_src = f["root_source"]
    if root_src.get("status") != "ok":
        out["boots_from_nvme"] = {
            "claim": "root filesystem is on NVMe",
            "result": "unknown",
            "evidence": root_src,
        }
    else:
        kind = root_src.get("kind")
        on_nvme = kind == "nvme"
        # Say what was actually found. "Removable storage" is true of an SD card
        # and false of a tmpfs or an NFS root, and a verdict that guesses wrong
        # about the failure sends the student to the wrong fix.
        why = {
            "nvme": "",
            "removable_or_sata": (
                " — this unit boots from removable storage and will be slow all semester"
            ),
        }.get(kind, " — that is neither NVMe nor the SD card; find out what imaged"
                    " this unit before trusting any number measured on it")
        out["boots_from_nvme"] = {
            "claim": "root filesystem is on NVMe",
            "result": "pass" if on_nvme else "fail",
            "evidence": root_src,
            "detail": f"root is {root_src['value']}{why}",
        }

    nvme = f["nvme_present"]
    out["nvme_fitted"] = {
        "claim": "an NVMe drive is fitted and visible",
        "result": "pass" if nvme.get("value") else "fail",
        "evidence": nvme,
    }

    mem = f["memory_total_kb"]
    if mem.get("status") != "ok":
        out["memory_visible"] = {
            "claim": "at least 6 GB of RAM is visible to Linux",
            "result": "unknown",
            "evidence": mem,
        }
    else:
        gb = mem["value"] / (1024 * 1024)
        enough = gb >= 6.0
        # The carveout note explains why an 8 GB module shows ~7.3 GiB. It does
        # not explain 2 GiB, and offering it there would talk a student out of
        # investigating a machine that is genuinely wrong.
        note = (
            "the carveout for GPU and hardware is taken before Linux sees the pool"
            if enough
            else "an 8 GB Orin Nano should show about 7.3 GiB — this is not a carveout, this is the wrong machine or a wrong reading"
        )
        out["memory_visible"] = {
            "claim": "at least 6 GB of RAM is visible to Linux",
            "result": "pass" if enough else "fail",
            "evidence": mem,
            "detail": f"{gb:.2f} GiB visible; {note}",
        }

    link = f["pcie_link"]
    if link.get("status") != "ok" or not link.get("negotiated"):
        out["pcie_link_understood"] = {
            "claim": "the negotiated PCIe link is known and explained",
            "result": "unknown",
            "evidence": link,
        }
    else:
        neg = link["negotiated"]
        out["pcie_link_understood"] = {
            "claim": "the negotiated PCIe link is known and explained",
            "result": "pass" if neg.get("gen") and neg.get("width") else "unknown",
            "evidence": link,
            "detail": link.get("interpretation"),
        }

    return out


def build(root: Path = Path("/"), device_id: str = "unknown") -> dict[str, Any]:
    """The whole report: findings, verdicts, and a one-line summary."""
    report = collect(root=root, device_id=device_id)
    report["verdicts"] = verdicts(report)
    results = [v["result"] for v in report["verdicts"].values()]
    report["summary"] = {
        "pass": results.count("pass"),
        "fail": results.count("fail"),
        "unknown": results.count("unknown"),
        "ready_for_labs": results.count("fail") == 0 and results.count("unknown") == 0,
    }
    return report
