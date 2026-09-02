"""What Lab 01's code package declares about itself.

INSTRUCTOR TOOLING. Everything here is Lab 01 specific; the machinery that reads
it lives in `instructor/labkit/`.

    python3 -m labkit gate labs/lab01
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "instructor"))

from labkit import ExitCase, LabConfig, Mutant  # noqa: E402

# Per-function hints. Deliberately about *what to read and what to return*, never
# about how to parse it — the parsing is the work.
HINTS: dict[str, list[str]] = {
    "probe_module_model": [
        "Read /proc/device-tree/model with the read_text helper.",
        "That node is NUL-terminated; read_text already strips it for you.",
        "Return {'value': <the string>, 'source': src, 'status': 'ok'},",
        "or unknown(src, <why>) if the node is not there.",
    ],
    "probe_memory_total_kb": [
        "Read /proc/meminfo and find the MemTotal line.",
        "Anchor your match to the start of a line, and return an int of kB,",
        "not the string and not the whole line.",
    ],
    "probe_root_source": [
        "Read /proc/mounts. Each line is: device mountpoint fstype options ...",
        "Find the line whose mountpoint is exactly '/' — it is not always first,",
        "and '/var' is not '/'.",
        "Return 'value' (the device) and also 'kind', one of:",
        "    'nvme'               device starts with /dev/nvme",
        "    'removable_or_sata'  device starts with /dev/mmcblk or /dev/sd",
        "    'other'              anything else, e.g. a tmpfs or NFS root",
        "The 'kind' field is what the verdict in report.py branches on.",
    ],
    "probe_nvme_present": [
        "Does <root>/sys/block/nvme0n1 exist?",
        "This must NOT look at what the root filesystem is mounted from. A board",
        "can have an NVMe fitted and still boot from the SD card, and telling",
        "those two apart is the entire point of the lab.",
        "Return 'value' as a bool, plus 'model' from",
        "/sys/block/nvme0n1/device/model if you can read it, else None.",
    ],
    "_parse_link_line": [
        "Pull the speed and width out of one LnkSta: or LnkCap: line.",
        "_SPEED_RE and _WIDTH_RE above already match them.",
        "Return {'raw', 'gts', 'width', 'gen'} — map GT/s to a generation with",
        "_GEN_BY_GTS, and use None for anything the line does not state.",
    ],
    "probe_pcie_link": [
        "Use `text` below — it is either the lspci output handed in by a test or",
        "the real thing. If it is empty, that is an unknown, not a failure.",
        "Find the LnkSta: line and the LnkCap: line and parse BOTH with",
        "_parse_link_line. Two numbers, kept separate:",
        "    negotiated  what the link actually came up at   (LnkSta)",
        "    capability  what the drive could have done      (LnkCap)",
        "Without sudo, lspci often prints no LnkCap at all. Report that as",
        "capability=None. Do not fill it in from LnkSta.",
        "If both generations are known, add an 'interpretation' string saying",
        "either that the drive is capped by the slot, or that it is running at",
        "full capability.",
    ],
    "probe_thermal_zones": [
        "Walk <root>/sys/class/thermal/thermal_zone*/.",
        "Each zone has a 'temp' file in MILLIDEGREES and a 'type' file.",
        "Divide by 1000. A board does not idle at 43,000 degrees.",
        "Return 'zones' (a list of {'zone', 'type', 'temp_c'}) and 'value' as the",
        "hottest zone. A zone can legitimately read below zero.",
        "Directory absent, or present with nothing readable in it, are both",
        "unknown — and neither of them is 0.0.",
    ],
    "probe_power_mode": [
        "Use `text` below, as with the PCIe probe.",
        "Parse the mode name out of the 'NV Power Mode: <name>' line, and the",
        "numeric mode id off the line by itself if there is one.",
        "nvpmodel does not exist off a Jetson. That is expected, and it is an",
        "unknown with a reason, not a crash.",
    ],
}

BANNER = """\
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
"""

BANNER_MARKER = (
    "# ---------------------------------------------------------------------------\n"
    "# The probes.\n"
)

CONFIG = LabConfig(
    lab_id="lab01",
    root=HERE,
    stub_module="enee459l/probes.py",
    stub_functions=[
        "probe_module_model",
        "probe_memory_total_kb",
        "probe_root_source",
        "probe_nvme_present",
        "_parse_link_line",
        "probe_pcie_link",
        "probe_thermal_zones",
        "probe_power_mode",
    ],
    hints=HINTS,
    banner=BANNER,
    cli="system_report.py",
    banner_marker=BANNER_MARKER,
    leak_patterns={
        "MemTotal regex": r"\^MemTotal:",
        "kind classification": r'kind = "removable_or_sata"',
        "interpretation text": r"whose M\.2 Key-M slot is wired Gen3 x4",
        "millidegree division": r'"temp_c": int\(raw\) / 1000\.0',
    },
    text_swaps=[
        (
            "enee459l/probes.py",
            "INSTRUCTOR SOLUTION. Do not distribute. The student copy of this file has the\n"
            "body of every function below replaced by `raise NotImplementedError`.",
            "STUDENT STARTER. Implement every function marked with a TODO below.",
        ),
        (
            "system_report.py",
            "INSTRUCTOR SOLUTION. Identical to the student copy; the difference between the\n"
            "two trees is `enee459l/probes.py`, which students implement.",
            "Provided complete. You do not need to change this file — the work is in\n"
            "`enee459l/probes.py`. Read it anyway: it is where the exit codes are decided,\n"
            "and you will be asked about them.",
        ),
    ],
    exit_cases=[
        ExitCase("nvme_good", 2, "lspci and nvpmodel are absent off-target, so the PCIe verdict is unknown"),
        ExitCase("sd_boot", 1, "boots_from_nvme fails — the failure this lab exists to teach"),
        ExitCase("bare", 1, "root is tmpfs and no NVMe is fitted"),
    ],
    mutants=[
        Mutant(
            "hardcodes-slash",
            "enee459l/probes.py",
            'p = Path(root) / rel.lstrip("/")',
            'p = Path("/") / rel.lstrip("/")',
        ),
        Mutant(
            "meminfo-substring-match",
            "enee459l/probes.py",
            r'r"^MemTotal:\s+(\d+)\s*kB", raw, re.MULTILINE',
            r'r"MemTotal:\s+(\d+)\s*kB", raw, re.MULTILINE',
        ),
        Mutant(
            "root-is-any-mountpoint",
            "enee459l/probes.py",
            'if len(parts) >= 2 and parts[1] == "/":',
            'if len(parts) >= 2 and parts[1].startswith("/"):',
        ),
        Mutant(
            "capability-copied-from-status",
            "enee459l/probes.py",
            "capability = _parse_link_line(cap) if cap else None",
            "capability = _parse_link_line(sta)",
        ),
        Mutant(
            "thermal-first-zone-not-max",
            "enee459l/probes.py",
            '"value": max(z["temp_c"] for z in zones),',
            '"value": zones[0]["temp_c"],',
        ),
        Mutant(
            "thermal-millidegrees-left-raw",
            "enee459l/probes.py",
            '"temp_c": int(raw) / 1000.0',
            '"temp_c": int(raw)',
        ),
        Mutant(
            "negative-temp-dropped",
            "enee459l/probes.py",
            'raw.lstrip("-").isdigit()',
            "raw.isdigit()",
        ),
        Mutant(
            "unknown-becomes-zero",
            "enee459l/probes.py",
            'return {"value": None, "source": source, "status": "unknown", "detail": why}',
            'return {"value": 0, "source": source, "status": "unknown", "detail": why}',
        ),
        Mutant(
            "empty-thermal-dir-reports-zero",
            "enee459l/probes.py",
            'return unknown(src, "thermal zone directory present but no readable temp nodes")',
            'return {"value": 0.0, "zones": [], "source": src, "status": "ok"}',
        ),
        Mutant(
            "sata-called-nvme",
            "enee459l/probes.py",
            'elif device.startswith(("/dev/mmcblk", "/dev/sd")):',
            'elif device.startswith(("/dev/mmcblk",)):',
        ),
        Mutant(
            "gen-lookup-by-stripped-string",
            "enee459l/probes.py",
            "gts = float(speed.group(1)) if speed else None",
            'gts = speed.group(1).rstrip(".0") if speed else None',
        ),
    ],
    # The benchmark record is the course's shared artifact rather than Lab 01's,
    # but Lab 01 is the first lab to depend on it, so it is gated here until a
    # second lab needs it too.
    extra_checks=[
        ("benchmark harness tests", ["-m", "pytest", "test_bench.py", "-q", "--no-header"], "../../common/bench"),
        ("reference record validates", ["validate.py", "reference/reference_record.json"], "../../common/bench"),
        ("JSON Schema agrees", ["check_schema.py"], "../../common/bench"),
    ],
)
