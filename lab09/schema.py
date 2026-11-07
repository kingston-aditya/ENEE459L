from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
LAB = "lab09"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNKNOWN = 2
EXIT_MALFORMED = 3

# How close a hand-folded convolution has to land to the reference before the
# fold counts as the same function. Three units in the last place of float32 is
# about 3.6e-7; 1e-5 leaves nearly two decimal orders of headroom, which is
# enough that an honest fold never fails and not enough that `sqrt(var) + eps`
# passes. Lecture 09 slide 18 measures the real gap.
FUSION_REL_TOL = 1e-5

# The default floor under a relative-error denominator. Chosen to be small
# against a logit and enormous against the near-zero entries that produce the
# lie; `max_rel_dev` reports how many entries hit it so the choice is visible
# rather than buried.
REL_FLOOR = 1e-3

# Which percentiles a latency table carries. A tuple, not three literals, so a
# lab that adds p99.9 adds it in one place.
LATENCY_PERCENTILES = (50, 95, 99)

# The three backends Stage D runs, in the order the table is drawn. The first
# is the reference every deviation is measured against, which is why it is
# first and why it is the framework rather than the engine: comparing the
# engine against itself is the mistake this ordering prevents.
BACKENDS = ("framework", "onnxruntime", "tensorrt")

# What has to be the same across everything in one session before any two
# numbers in it can be laid side by side. Same list as Labs 07 and 08 plus the
# two this lab is about.
FIXED_CONDITIONS = ("power_mode", "jetpack", "trt_version", "cuda_version",
                    "compute_capability")

REQUIRED = (
    "schema_version",
    "lab",
    "generated",
    "model",
    "conditions",
    "findings",
    "verdicts",
    "provenance",
    "notes",
)

# What a session must carry before it is a session. Five keys beyond the shared
# header, one per lettered stage, and every one of them is nullable except
# `export` and `fusion` -- which are the two Stage A produces and Stage A needs
# no board.
REQUIRED_SESSION = (
    "schema_version",
    "lab",
    "generated",
    "device_id",
    "model",
    "conditions",
    "export",
    "fusion",
    "builds",
    "refusal",
    "backends",
    "record",
)

REQUIRED_MODEL = ("name", "source", "sha256", "opset", "ir_version",
                  "input_name", "input_shape", "classes")

REQUIRED_EXPORT = ("exporter", "initializers", "nodes")

# The six per-channel parameter arrays, the convolution they fold into, the
# epsilon, and the reference. `reference_weight` and `reference_bias` are what
# the two layers produce when they are run separately -- the answer the fusion
# has to reproduce -- and the checker recomputes the fold with the student's
# own `fold_batchnorm` and compares against them. Nothing here records what the
# student's bench script printed: a verdict that read a number out of the
# session it is judging would pass for a session that wrote the number down
# wrong in exactly the same way twice.
REQUIRED_FUSION = ("eps", "weight", "bias", "gamma", "beta", "mean", "var",
                   "reference_weight", "reference_bias")

REQUIRED_BUILD = ("precision", "seconds", "onnx_bytes", "plan_bytes",
                  "workspace_mib", "profile")

REQUIRED_REFUSAL = ("attempted", "message", "plan", "machine")

REQUIRED_BACKEND = ("name", "precision", "latency_ms", "outputs")

FINDING_STATUSES = ("ok", "note", "warn", "fail")
VERDICT_RESULTS = ("pass", "fail", "unknown")


class SchemaError(ValueError):
    """A document this module refuses to call a session or a report."""


def _need(doc: Any, keys: tuple[str, ...], what: str) -> None:
    if not isinstance(doc, dict):
        raise SchemaError(f"{what} is {type(doc).__name__}, not an object.")
    missing = [k for k in keys if k not in doc]
    if missing:
        raise SchemaError(
            f"{what} has no " + ", ".join(repr(k) for k in missing)
            + ". A field that may be absent is a field somebody forgets, and "
            "the document still looks complete."
        )


def validate_session(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 09 session.

    Checks structure and the handful of values that make a document about a
    different thing rather than a document with a bad number in it. It does not
    check whether the numbers are any good; that is what the verdicts are for
    and the difference between the two is the difference between exit 3 and
    exit 1.
    """
    _need(doc, REQUIRED_SESSION, "the session")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(
            f"session schema {doc['schema_version']!r}; this tool reads "
            f"{SCHEMA_VERSION!r}."
        )
    if doc["lab"] != LAB:
        raise SchemaError(f"this is a {doc['lab']!r} session, not a {LAB} one.")

    _need(doc["model"], REQUIRED_MODEL, "model")
    m = doc["model"]
    for k in ("opset", "ir_version", "classes"):
        if isinstance(m[k], bool) or not isinstance(m[k], int) or m[k] <= 0:
            raise SchemaError(f"model.{k} is {m[k]!r}, which is not a positive integer.")
    if not isinstance(m["input_shape"], list) or not m["input_shape"]:
        raise SchemaError("model.input_shape is empty; an input with no axes is not an input.")

    _need(doc["conditions"], FIXED_CONDITIONS, "conditions")

    _need(doc["export"], REQUIRED_EXPORT, "export")
    if not isinstance(doc["export"]["nodes"], list) or not doc["export"]["nodes"]:
        raise SchemaError("export.nodes is empty; a graph with no nodes is not a graph.")

    _need(doc["fusion"], REQUIRED_FUSION, "fusion")

    if doc["builds"] is not None:
        if not isinstance(doc["builds"], list):
            raise SchemaError("builds is present and is not a list.")
        for i, b in enumerate(doc["builds"]):
            _need(b, REQUIRED_BUILD, f"builds[{i}]")

    if doc["refusal"] is not None:
        _need(doc["refusal"], REQUIRED_REFUSAL, "refusal")
        if not isinstance(doc["refusal"]["attempted"], bool):
            raise SchemaError(
                "refusal.attempted is not a boolean. `false` is a real value "
                "and means Stage C did not run; `null` here would make "
                "'did not run' and 'ran and told us nothing' the same state."
            )

    if doc["backends"] is not None:
        if not isinstance(doc["backends"], list):
            raise SchemaError("backends is present and is not a list.")
        for i, b in enumerate(doc["backends"]):
            _need(b, REQUIRED_BACKEND, f"backends[{i}]")
            if not isinstance(b["latency_ms"], list) or not b["latency_ms"]:
                raise SchemaError(f"backends[{i}].latency_ms is empty.")
            for j, v in enumerate(b["latency_ms"]):
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise SchemaError(
                        f"backends[{i}].latency_ms[{j}] is {v!r}, not a duration."
                    )
                if float(v) < 0.0:
                    raise SchemaError(
                        f"backends[{i}].latency_ms[{j}] is {v}. A negative "
                        "duration is two clocks, not a fast backend, and no "
                        "report can be built on top of it."
                    )
            if not isinstance(b["outputs"], list) or not b["outputs"]:
                raise SchemaError(f"backends[{i}].outputs is empty.")

    if doc["record"] is not None and not isinstance(doc["record"], dict):
        raise SchemaError("record is present and is not an object.")


def validate(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 09 report."""
    _need(doc, REQUIRED, "the report")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(
            f"report schema {doc['schema_version']!r}; this tool writes "
            f"{SCHEMA_VERSION!r}."
        )
    if doc["lab"] != LAB:
        raise SchemaError(f"this is a {doc['lab']!r} report, not a {LAB} one.")
    if not isinstance(doc["findings"], list):
        raise SchemaError("findings is not a list.")
    for i, f in enumerate(doc["findings"]):
        _need(f, ("status", "message"), f"findings[{i}]")
        if f["status"] not in FINDING_STATUSES:
            raise SchemaError(
                f"findings[{i}].status is {f['status']!r}; one of "
                + ", ".join(FINDING_STATUSES)
            )
    if not isinstance(doc["verdicts"], list) or not doc["verdicts"]:
        raise SchemaError(
            "verdicts is empty. A report with no verdicts exits 0 by "
            "arithmetic and says nothing, which is the worst of the four "
            "outcomes because it looks like the best."
        )
    for i, v in enumerate(doc["verdicts"]):
        _need(v, ("name", "result", "because"), f"verdicts[{i}]")
        if v["result"] not in VERDICT_RESULTS:
            raise SchemaError(
                f"verdicts[{i}].result is {v['result']!r}; one of "
                + ", ".join(VERDICT_RESULTS)
            )
        if not str(v["because"]).strip():
            raise SchemaError(
                f"verdicts[{i}] ({v['name']}) has an empty reason. A verdict "
                "without a sentence is a number somebody has to take on trust."
            )


def exit_code(verdicts: list[dict[str, Any]]) -> int:
    """The exit code these verdicts earn. Fail dominates unknown.

    A report carrying one failure and six unknowns exits 1, because a student
    who fixes the six unknowns and re-runs would otherwise see the exit code
    change from 2 to 1 and read it as a regression.
    """
    results = [v["result"] for v in verdicts]
    if any(r == "fail" for r in results):
        return EXIT_FAILED
    if any(r == "unknown" for r in results):
        return EXIT_UNKNOWN
    return EXIT_OK