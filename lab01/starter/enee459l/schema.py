"""The shape a Lab 01 system report must have, and a validator for it.

Provided complete in both trees. The validator is deliberately dependency-free
so it runs on a freshly imaged board before anybody has pip-installed anything,
which is the exact moment Lab 01 needs it.

Why a schema at all, for a nine-field report: twenty groups hand in twenty
files, and Assignment 1 compares them. Without a fixed shape that comparison
becomes twenty ad-hoc parsers. This is the same argument as doc 02 §8's
benchmark record, one lab earlier and one size smaller.
"""

from __future__ import annotations

from typing import Any

REQUIRED_TOP = ("schema_version", "device_id", "collected_at", "findings", "verdicts", "summary")

REQUIRED_FINDINGS = (
    "module_model",
    "memory_total_kb",
    "root_source",
    "nvme_present",
    "pcie_link",
    "thermal",
    "power_mode",
)

REQUIRED_VERDICTS = ("boots_from_nvme", "nvme_fitted", "memory_visible", "pcie_link_understood")

VALID_RESULTS = ("pass", "fail", "unknown")


class ValidationError(Exception):
    """Raised with every problem found, not just the first."""


def validate(report: Any) -> list[str]:
    """Return a list of problems. An empty list means the report is valid.

    Returns rather than raises so that a student can see all of what is wrong
    in one run instead of playing whack-a-mole with the first error.
    """
    problems: list[str] = []

    if not isinstance(report, dict):
        return [f"report must be a JSON object, got {type(report).__name__}"]

    for key in REQUIRED_TOP:
        if key not in report:
            problems.append(f"missing top-level key: {key}")

    findings = report.get("findings")
    if not isinstance(findings, dict):
        problems.append("findings must be an object")
    else:
        for key in REQUIRED_FINDINGS:
            if key not in findings:
                problems.append(f"missing finding: {key}")
                continue
            item = findings[key]
            if not isinstance(item, dict):
                problems.append(f"finding {key} must be an object")
            elif "source" not in item:
                # The rule the whole course rests on: a value without a source
                # is not evidence. Enforced here so it fails at the bench.
                problems.append(f"finding {key} has no 'source' — a value without provenance is not evidence")

    verdicts = report.get("verdicts")
    if not isinstance(verdicts, dict):
        problems.append("verdicts must be an object")
    else:
        for key in REQUIRED_VERDICTS:
            if key not in verdicts:
                problems.append(f"missing verdict: {key}")
                continue
            v = verdicts[key]
            if not isinstance(v, dict):
                problems.append(f"verdict {key} must be an object")
                continue
            if v.get("result") not in VALID_RESULTS:
                problems.append(
                    f"verdict {key} has result {v.get('result')!r}, expected one of {VALID_RESULTS}"
                )
            if "evidence" not in v:
                problems.append(f"verdict {key} has no 'evidence' — a claim without evidence is an opinion")

    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in ("pass", "fail", "unknown", "ready_for_labs"):
            if key not in summary:
                problems.append(f"summary missing key: {key}")
    elif "summary" in report:
        problems.append("summary must be an object")

    return problems


def assert_valid(report: Any) -> None:
    """Raise ValidationError listing every problem, or return silently."""
    problems = validate(report)
    if problems:
        raise ValidationError(
            f"{len(problems)} problem(s) in system report:\n  - " + "\n  - ".join(problems)
        )
