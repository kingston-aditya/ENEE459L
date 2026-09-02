#!/usr/bin/env python3
"""ENEE459L Lab 01 — produce a machine-readable report of what this board is.

Provided complete. You do not need to change this file — the work is in
`enee459l/probes.py`. Read it anyway: it is where the exit codes are decided,
and you will be asked about them.

    python3 system_report.py --device-id jetson-07 -o system_report.json

Exit status is part of the interface, because this script is meant to be run
from other scripts and from CI later in the semester:

    0  every verdict passed
    1  at least one verdict failed — the machine needs attention
    2  at least one verdict is unknown and none failed — the measurement needs
       attention, which is a different problem with a different fix
    3  the report did not match the schema, which is a bug in the code

The three-way split at the top is the point. "It didn't work" is not a bug
report; "the probe could not read /proc/mounts" is.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from enee459l import report as report_mod
from enee459l import schema

EXIT_OK = 0
EXIT_FAILED_VERDICT = 1
EXIT_UNKNOWN_VERDICT = 2
EXIT_BAD_SCHEMA = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Collect and verify what this Jetson says about itself.",
        epilog="Hand in the JSON, not a screenshot of the terminal.",
    )
    p.add_argument(
        "--device-id",
        default="unknown",
        help="the label on the physical unit, e.g. jetson-07. Use the sticker, not the hostname.",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("system_report.json"),
        help="where to write the report (default: %(default)s)",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=Path("/"),
        help=argparse.SUPPRESS,  # test seam; not part of the student-facing interface
    )
    p.add_argument("-q", "--quiet", action="store_true", help="write the file, print nothing")
    return p.parse_args(argv)


def render_human(rep: dict) -> str:
    """A short console summary. The JSON is the artifact; this is for the bench."""
    lines = []
    mark = {"pass": "PASS", "fail": "FAIL", "unknown": "????"}
    for name, v in rep["verdicts"].items():
        lines.append(f"  {mark.get(v['result'], '????'):5s} {name:24s} {v['claim']}")
        detail = v.get("detail")
        if detail:
            lines.append(f"        {detail}")
    s = rep["summary"]
    lines.append("")
    lines.append(
        f"  {s['pass']} passed, {s['fail']} failed, {s['unknown']} unknown"
        f" — {'ready for labs' if s['ready_for_labs'] else 'NOT ready for labs'}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rep = report_mod.build(root=args.root, device_id=args.device_id)

    problems = schema.validate(rep)
    if problems:
        print("system report does not match the schema:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return EXIT_BAD_SCHEMA

    args.output.write_text(json.dumps(rep, indent=2, sort_keys=False) + "\n")

    if not args.quiet:
        print(f"ENEE459L Lab 01 system report — device {rep['device_id']}")
        print(render_human(rep))
        print(f"\n  written to {args.output}")

    if rep["summary"]["fail"]:
        return EXIT_FAILED_VERDICT
    if rep["summary"]["unknown"]:
        return EXIT_UNKNOWN_VERDICT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
