from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
LAB = "lab10"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNKNOWN = 2
EXIT_MALFORMED = 3

# The rate this lab captures at, and the rate every number in the handout was
# computed for. It is not a constant because the code assumes it -- `bin_width`
# and `frame_rate` both take a rate argument -- it is a constant because the
# session has to be able to say that the file was captured at something else,
# and a verdict has to be able to notice.
SR_LAB = 16000

# A canonical PCM WAV header: RIFF, fmt with sixteen bytes of payload, data.
# Forty-four bytes, and a capture tool that writes a LIST chunk writes more.
# `the_header_agrees_with_the_bytes` uses the number the session recorded, not
# this one; this is what the number is checked against for plausibility.
WAV_HEADER_BYTES = 44

# Twenty times the log of two. One bit of depth is this many decibels of range,
# which is where 96.33 dB for int16 comes from and where "nine and a third bits
# in use at minus forty" comes from. Written to four places because it is
# printed, not because it is uncertain.
DB_PER_BIT = 6.020599913279624

# How close a recomputed Mel edge has to land to the reference before the two
# count as the same filterbank. The warp is a log and a division; a correct
# implementation lands within a few units in the last place, and 1e-9 leaves
# several decimal orders of headroom while still refusing the 2595-versus-1127
# constant substitution, which is off in the fourth significant figure.
MEL_REL_TOL = 1e-9

# The window in which a captured level is neither clipped nor buried. Above
# -1 dBFS an int16 signal is close enough to the rail that a louder syllable
# would have flattened; below -40 dBFS fewer than ten of the sixteen bits are
# doing anything and the quantisation floor has climbed into the signal.
# Lecture 10 slide 9 draws the ladder these two sit on.
PEAK_DBFS_MAX = -1.0
PEAK_DBFS_MIN = -40.0

# What fraction of samples may sit at full scale before the capture counts as
# clipped. Not zero: a single sample at the rail in a hundred and sixty thousand
# is a cosmic ray, and a verdict that fails on it teaches students to distrust
# the verdict. One in ten thousand is four samples a second and is audible.
CLIP_RATE_MAX = 1e-4

# The six stages a front end spends its milliseconds in, in the order the
# arithmetic runs and the order the table is drawn.
STAGES = ("read", "frame", "window", "rfft", "mel", "dct")

# What has to be the same across everything in one session before any two
# numbers in it can be laid side by side. The same five as Labs 07 through 09.
FIXED_CONDITIONS = ("power_mode", "jetpack", "trt_version", "cuda_version",
                    "compute_capability")

# The thirteen choices from Lecture 10 slide 50, in the order the figure draws
# them. Three of them are in the WAV header and the other ten are in nothing at
# all unless somebody writes them down, which is what Stage E is.
#
# fmin and fmax are not on this list. They are two more choices and they belong
# on it; thirteen is the number the lecture drew and this tuple is here so the
# lab and the lecture do not drift, not because thirteen is complete.
THIRTEEN_CHOICES = (
    "capture_device",
    "sample_rate",
    "bit_depth",
    "channels",
    "capture_gain",
    "frame_length",
    "hop_length",
    "window",
    "power_or_magnitude",
    "n_mels",
    "log_floor",
    "n_mfcc",
    "normalisation",
)

# Which of the thirteen the file itself records. A student who has these three
# has three; the verdict is about the other ten.
CHOICES_IN_HEADER = ("sample_rate", "bit_depth", "channels")

REQUIRED = (
    "schema_version",
    "lab",
    "generated",
    "audio",
    "conditions",
    "findings",
    "verdicts",
    "provenance",
    "notes",
)

# What a session must carry before it is a session. Five keys beyond the shared
# header and the plan, one per lettered stage, and every one of those five is
# nullable -- `plan` is not, because Stage A needs no board.
REQUIRED_SESSION = (
    "schema_version",
    "lab",
    "generated",
    "device_id",
    "audio",
    "conditions",
    "plan",
    "capture",
    "amplitude",
    "framing",
    "features",
    "record",
)

REQUIRED_AUDIO = ("name", "source", "sha256", "sample_rate", "channels",
                  "bit_depth", "seconds", "samples")

# The eleven choices that fix every shape downstream, plus the three shapes the
# library actually produced. `observed_shapes` is what the student's front end
# printed; the checker recomputes all three from the other eleven using the
# student's own `feature_shapes` and compares. Nothing here records what the
# student *thought* the shape would be: a verdict that read its own answer out
# of the session it is judging would pass for a session that got the same thing
# wrong twice.
REQUIRED_PLAN = ("sample_rate", "samples", "window", "hop", "centred", "n_fft",
                 "n_mels", "n_mfcc", "fmin", "fmax", "floor_db", "power",
                 "observed_shapes")

REQUIRED_SHAPES = ("spectrogram", "mel", "mfcc")

# Stage A on the board. `devices` is what enumeration printed, `chosen` is the
# name that was captured from, `command` is the invocation verbatim -- and the
# reason it is verbatim is that a paraphrased command is a command nobody can
# re-run, which is the sentence every lab deck in this course closes on.
REQUIRED_CAPTURE = ("devices", "chosen", "command", "seconds", "bytes",
                    "header")

REQUIRED_DEVICE = ("index", "name", "card", "device")

REQUIRED_HEADER = ("channels", "sample_rate", "bit_depth", "data_bytes",
                   "header_bytes")

# Stage B. Amplitudes are fractions of full scale; see the module docstring.
REQUIRED_AMPLITUDE = ("peak", "rms", "clipped", "samples", "noise_floor")

# Stage C. Two framings of one file, counted, plus enough of the window to say
# which window it was. Five coefficients is enough to separate a periodic Hann
# from a symmetric one at any length this lab uses, and short enough to read.
REQUIRED_FRAMING = ("uncentred", "centred", "window_name", "coefficients")

REQUIRED_FRAMING_CASE = ("frames", "covered", "uncovered")

# Stage D. One millisecond per stage, the frame count they were measured over,
# and which implementation produced them.
REQUIRED_FEATURES = ("backend", "frames", "hop_ms", "stage_ms")

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


def _pos_int(v: Any, what: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise SchemaError(f"{what} is {v!r}, which is not a positive integer.")
    return v


def _number(v: Any, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SchemaError(f"{what} is {v!r}, which is not a number.")
    return float(v)


def validate_session(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 10 session.

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

    _need(doc["audio"], REQUIRED_AUDIO, "audio")
    a = doc["audio"]
    for k in ("sample_rate", "channels", "bit_depth", "samples"):
        _pos_int(a[k], f"audio.{k}")
    if _number(a["seconds"], "audio.seconds") <= 0.0:
        raise SchemaError(
            f"audio.seconds is {a['seconds']!r}. A recording of no length is "
            "a file that was opened and not written to, and every count in "
            "this report divides by it."
        )

    _need(doc["conditions"], FIXED_CONDITIONS, "conditions")

    _validate_plan(doc["plan"])

    if doc["capture"] is not None:
        _validate_capture(doc["capture"])
    if doc["amplitude"] is not None:
        _validate_amplitude(doc["amplitude"])
    if doc["framing"] is not None:
        _validate_framing(doc["framing"])
    if doc["features"] is not None:
        _validate_features(doc["features"])
    if doc["record"] is not None and not isinstance(doc["record"], dict):
        raise SchemaError("record is present and is not an object.")


def _validate_plan(plan: Any) -> None:
    _need(plan, REQUIRED_PLAN, "plan")
    for k in ("sample_rate", "samples", "window", "hop", "n_fft", "n_mels",
              "n_mfcc"):
        _pos_int(plan[k], f"plan.{k}")
    if not isinstance(plan["centred"], bool):
        raise SchemaError(
            "plan.centred is not a boolean. It is the difference between "
            "ninety-eight frames and a hundred and one, and a front end that "
            "does not know which one it did cannot be compared with anything."
        )
    for k in ("fmin", "fmax", "floor_db"):
        _number(plan[k], f"plan.{k}")
    if plan["fmin"] >= plan["fmax"]:
        raise SchemaError(
            f"plan.fmin is {plan['fmin']} and plan.fmax is {plan['fmax']}. "
            "A band that ends before it starts has no triangles in it."
        )
    pw = plan["power"]
    if isinstance(pw, bool) or not isinstance(pw, int) or pw not in (1, 2):
        raise SchemaError(
            f"plan.power is {pw!r}; 1 for magnitude, 2 for power. These are "
            "the two conventions and a front end that squares when the model "
            "was trained on magnitude is off by a factor nothing downstream "
            "reports. It is an exponent and not a measurement, so 2.0 and "
            "true are refused here along with 3."
        )
    _need(plan["observed_shapes"], REQUIRED_SHAPES, "plan.observed_shapes")
    for k in REQUIRED_SHAPES:
        s = plan["observed_shapes"][k]
        if (not isinstance(s, list) or len(s) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0
                       for v in s)):
            raise SchemaError(
                f"plan.observed_shapes.{k} is {s!r}; two positive integers, "
                "bins first and frames second, the way the library returned it."
            )


def _validate_capture(cap: Any) -> None:
    _need(cap, REQUIRED_CAPTURE, "capture")
    if not isinstance(cap["devices"], list) or not cap["devices"]:
        raise SchemaError(
            "capture.devices is empty. A board with no capture device is a "
            "finding about the board; a session that records none is a "
            "session where enumeration was not run."
        )
    for i, d in enumerate(cap["devices"]):
        _need(d, REQUIRED_DEVICE, f"capture.devices[{i}]")
    _pos_int(cap["bytes"], "capture.bytes")
    if _number(cap["seconds"], "capture.seconds") <= 0.0:
        raise SchemaError(f"capture.seconds is {cap['seconds']!r}.")
    _need(cap["header"], REQUIRED_HEADER, "capture.header")
    h = cap["header"]
    for k in ("channels", "sample_rate", "bit_depth", "data_bytes",
              "header_bytes"):
        _pos_int(h[k], f"capture.header.{k}")


def _validate_amplitude(amp: Any) -> None:
    _need(amp, REQUIRED_AMPLITUDE, "amplitude")
    _pos_int(amp["samples"], "amplitude.samples")
    if isinstance(amp["clipped"], bool) or not isinstance(amp["clipped"], int) \
            or amp["clipped"] < 0:
        raise SchemaError(
            f"amplitude.clipped is {amp['clipped']!r}, which is not a count.")
    if amp["clipped"] > amp["samples"]:
        raise SchemaError(
            f"amplitude.clipped is {amp['clipped']} of {amp['samples']} "
            "samples, which is more samples than there are.")
    for k in ("peak", "rms"):
        v = _number(amp[k], f"amplitude.{k}")
        if v < 0.0 or v > 1.0:
            raise SchemaError(
                f"amplitude.{k} is {v}. Amplitudes here are fractions of full "
                "scale in [0, 1]. A value above one is an int16 count or a "
                "dBFS that lost its sign, and both look like a loud signal "
                "from here."
            )
    if amp["rms"] > amp["peak"]:
        raise SchemaError(
            f"amplitude.rms is {amp['rms']} and amplitude.peak is "
            f"{amp['peak']}. No signal has a root mean square above its own "
            "maximum; these two were measured on different arrays."
        )
    if amp["noise_floor"] is not None:
        nf = _number(amp["noise_floor"], "amplitude.noise_floor")
        if nf > 0.0:
            raise SchemaError(
                f"amplitude.noise_floor is {nf} dBFS. Full scale is zero and "
                "everything below it is negative; a positive dBFS is a level "
                "above the largest number the format holds."
            )


def _validate_framing(fr: Any) -> None:
    _need(fr, REQUIRED_FRAMING, "framing")
    for k in ("uncentred", "centred"):
        _need(fr[k], REQUIRED_FRAMING_CASE, f"framing.{k}")
        case = fr[k]
        for f in ("frames", "covered", "uncovered"):
            v = case[f]
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise SchemaError(
                    f"framing.{k}.{f} is {v!r}, which is not a count.")
        if case["frames"] == 0:
            raise SchemaError(
                f"framing.{k}.frames is zero. A framing that produced no "
                "frames is a window longer than the file, and the report for "
                "it is about the window."
            )
    if not isinstance(fr["coefficients"], list) or len(fr["coefficients"]) < 2:
        raise SchemaError(
            "framing.coefficients holds fewer than two numbers. It is the "
            "head of the window array and it is what says which window this "
            "was; one number says only that the window starts somewhere."
        )
    for i, v in enumerate(fr["coefficients"]):
        _number(v, f"framing.coefficients[{i}]")


def _validate_features(ft: Any) -> None:
    _need(ft, REQUIRED_FEATURES, "features")
    _pos_int(ft["frames"], "features.frames")
    if _number(ft["hop_ms"], "features.hop_ms") <= 0.0:
        raise SchemaError(
            f"features.hop_ms is {ft['hop_ms']!r}. The hop is the budget and "
            "a budget of zero divides nothing."
        )
    _need(ft["stage_ms"], STAGES, "features.stage_ms")
    for k in STAGES:
        v = _number(ft["stage_ms"][k], f"features.stage_ms.{k}")
        if v < 0.0:
            raise SchemaError(
                f"features.stage_ms.{k} is {v}. A negative duration is two "
                "clocks, not a fast stage, and no report can be built on top "
                "of it."
            )


def validate(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 10 report."""
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