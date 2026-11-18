from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
LAB = "lab11"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNKNOWN = 2
EXIT_MALFORMED = 3

# The rate this lab streams at, and the rate every number in the handout was
# computed for. As in Lab 10 it is a constant so that the session can say the
# stream ran at something else and a verdict can notice, not because the code
# assumes it.
SR_LAB = 16000

# Seconds in an hour. Spelled once, because "per hour" appears in four modules
# and 3600 written out in each of them is four places for a 360 to hide.
SECONDS_PER_HOUR = 3600.0

# How close the student's stated arithmetic has to land to the checker's before
# the two count as the same number. Half a millisecond: every term in the
# ladder is a product of a hop and a small integer, so a correct answer is
# exact and this tolerance exists only to absorb the way a float divides.
LADDER_TOL_MS = 0.5

# The same, for the ring. A ring is a block count times a block length and it
# is exact too.
RING_TOL_MS = 0.5

# The same, for decisions an hour, which is 3600 over the hop and can be a
# recurring decimal.
RATE_TOL_PER_HOUR = 0.5

# A loop whose work exceeds its hop does not fall behind slowly. It falls
# behind at a rate the ring cannot absorb, and the ring's depth only sets how
# long you have before it notices. One is the wall.
RTF_MAX = 1.0

# And this is where the warning goes. Eighty per cent of the hop leaves two
# milliseconds in ten for the scheduler, the page fault, and the second process
# somebody started over SSH. Lecture 08 made this argument about frames; it is
# the same argument.
RTF_WARN = 0.8

# Below this, a word-level recall is not a detector any more, whatever it did
# to the false-trigger rate. There is no principle behind 0.85; it is the floor
# the handout asks students to hold while they tune, so that "I got the rate to
# zero" cannot be the answer.
RECALL_MIN = 0.85

# A rate measured over less than this is not a rate. Five minutes at a tenth of
# a second is three thousand decisions, which is enough for a rate of a few an
# hour to be more signal than noise. The handout asks for ten minutes.
QUIET_SECONDS_MIN = 300.0

# The letters Lab 11's stages are named with. Lettered, never numbered, and in
# the order the handout runs them.
STAGES = ("A", "B", "C", "D", "E")

# The four terms of the latency ladder, in the order Lecture 11 slide 34 draws
# them and the order `stream.latency_ladder` returns them.
LADDER_TERMS = ("event", "hop", "infer", "vote")

# What has to be the same across everything in one session before any two
# numbers in it can be laid side by side. The same five as Labs 07 through 10.
FIXED_CONDITIONS = ("power_mode", "jetpack", "trt_version", "cuda_version",
                    "compute_capability")

# The twelve choices a streaming detector is, from Lecture 11 slide 4 and its
# four parts. Two of them -- the block and the ring -- are fixed before a frame
# arrives; the other ten move between runs and will.
#
# The model is not on this list, and that is the lecture's point rather than an
# omission: not one of the twelve is a weight.
TWELVE_CHOICES = (
    "block_ms",
    "ring_blocks",
    "window_s",
    "hop_s",
    "threshold",
    "k",
    "n",
    "enter",
    "leave",
    "refractory_s",
    "collar_s",
    "power_mode",
)

# Which two of the twelve are settled before the stream starts. A student who
# has these two has the two that cost the least to change and the most to get
# wrong.
CHOICES_BEFORE_THE_STREAM = ("block_ms", "ring_blocks")

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
# nullable -- `plan` is not, because Stage A's arithmetic needs no board.
REQUIRED_SESSION = (
    "schema_version",
    "lab",
    "generated",
    "device_id",
    "audio",
    "conditions",
    "plan",
    "stream",
    "scores",
    "timing",
    "quiet",
    "events",
    "record",
)

REQUIRED_AUDIO = ("name", "source", "sha256", "sample_rate", "channels",
                  "bit_depth", "seconds", "samples")

# The fifteen numbers that fix every downstream quantity in this lab, plus the
# three the student worked out from them. `stated` is what the checker
# recomputes and compares; nothing here records what the board did, because
# none of these three needs a board.
REQUIRED_PLAN = ("sample_rate", "block_ms", "ring_blocks", "window_s", "hop_s",
                 "k", "n", "threshold", "enter", "leave", "refractory_s",
                 "collar_s", "event_s", "infer_ms", "ft_per_hour_max",
                 "stated")

REQUIRED_STATED = ("ring_ms", "latency_ms", "decisions_per_hour")

# Stage A. Three counts and the flags they came from. `drop_flags` is one
# boolean per block read, which is how the longest run is recoverable; a
# session that recorded only the total could not say whether ten drops were ten
# glitches or one gap.
REQUIRED_STREAM = ("seconds", "blocks_written", "blocks_read", "blocks_dropped",
                   "drop_flags")

# Stage B. One score per hop, one label per score, and the threshold that was
# drawn on the plot.
REQUIRED_SCORES = ("hop_s", "values", "labels", "threshold")

# Stage C. Two milliseconds and the hop they are spent against, plus the count
# they were averaged over. `backend` says which implementation, because an RTF
# with no backend beside it is a number about an afternoon.
REQUIRED_TIMING = ("backend", "hops", "hop_ms", "front_end_ms", "model_ms")

# Stage D. A rate is a count and a denominator, twice: once raw and once
# smoothed, with the recall each of them bought.
REQUIRED_QUIET = ("seconds", "threshold", "false_triggers",
                  "smoothed_false_triggers", "recall_before", "recall_after")

# Stage E. Two lists of onsets in seconds and the collar they are matched
# under. `log` is the rows the handout asks for and is checked for shape only;
# the verdict is about the onsets.
REQUIRED_EVENTS = ("collar_s", "predicted_s", "truth_s", "log")

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


def _count(v: Any, what: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise SchemaError(f"{what} is {v!r}, which is not a count.")
    return v


def _number(v: Any, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SchemaError(f"{what} is {v!r}, which is not a number.")
    return float(v)


def _score(v: Any, what: str) -> float:
    f = _number(v, what)
    if f < 0.0 or f > 1.0:
        raise SchemaError(
            f"{what} is {f}. Scores in this lab are in [0, 1]. A value outside "
            "it is a logit, a percentage or an unnormalised distance, and all "
            "three look like a confident model from here."
        )
    return f


def validate_session(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 11 session.

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
            f"audio.seconds is {a['seconds']!r}. A stream of no length is a "
            "device that was opened and never read, and every rate in this "
            "report divides by a duration."
        )

    _need(doc["conditions"], FIXED_CONDITIONS, "conditions")

    _validate_plan(doc["plan"])

    if doc["stream"] is not None:
        _validate_stream(doc["stream"])
    if doc["scores"] is not None:
        _validate_scores(doc["scores"])
    if doc["timing"] is not None:
        _validate_timing(doc["timing"])
    if doc["quiet"] is not None:
        _validate_quiet(doc["quiet"])
    if doc["events"] is not None:
        _validate_events(doc["events"])
    if doc["record"] is not None and not isinstance(doc["record"], dict):
        raise SchemaError("record is present and is not an object.")


def _validate_plan(plan: Any) -> None:
    _need(plan, REQUIRED_PLAN, "plan")
    _pos_int(plan["sample_rate"], "plan.sample_rate")
    for k in ("k", "n"):
        _pos_int(plan[k], f"plan.{k}")
    if plan["k"] > plan["n"]:
        raise SchemaError(
            f"plan.k is {plan['k']} of plan.n {plan['n']}. A rule that asks "
            "for more agreeing windows than it looks at can never fire, and a "
            "detector that never fires has a false-trigger rate of zero."
        )
    for k in ("block_ms", "window_s", "hop_s", "event_s", "infer_ms",
              "ft_per_hour_max"):
        if _number(plan[k], f"plan.{k}") <= 0.0:
            raise SchemaError(
                f"plan.{k} is {plan[k]!r}. Every duration and every budget in "
                "the plan is positive; a zero here is a field that was left "
                "for later and then shipped."
            )
    _pos_int(plan["ring_blocks"], "plan.ring_blocks")
    for k in ("refractory_s", "collar_s"):
        if _number(plan[k], f"plan.{k}") < 0.0:
            raise SchemaError(
                f"plan.{k} is {plan[k]!r}. Zero is allowed and means the "
                "mechanism is off; negative is a sign somebody flipped."
            )
    for k in ("threshold", "enter", "leave"):
        _score(plan[k], f"plan.{k}")
    if plan["leave"] > plan["enter"]:
        raise SchemaError(
            f"plan.leave is {plan['leave']} and plan.enter is {plan['enter']}. "
            "Hysteresis leaves below where it enters. The other way round is "
            "not a wider band, it is a detector that turns off before it has "
            "turned on."
        )
    if plan["hop_s"] > plan["window_s"]:
        raise SchemaError(
            f"plan.hop_s is {plan['hop_s']} against a window of "
            f"{plan['window_s']}. A hop longer than the window skips audio "
            "between decisions, and the samples in the gap were captured, "
            "paid for and never looked at."
        )
    _need(plan["stated"], REQUIRED_STATED, "plan.stated")
    for k in REQUIRED_STATED:
        if _number(plan["stated"][k], f"plan.stated.{k}") <= 0.0:
            raise SchemaError(
                f"plan.stated.{k} is {plan['stated'][k]!r}. These are three "
                "numbers worked out on paper before the board was switched "
                "on, and none of them is zero for any plan."
            )


def _validate_stream(st: Any) -> None:
    _need(st, REQUIRED_STREAM, "stream")
    if _number(st["seconds"], "stream.seconds") <= 0.0:
        raise SchemaError(f"stream.seconds is {st['seconds']!r}.")
    for k in ("blocks_written", "blocks_read", "blocks_dropped"):
        _count(st[k], f"stream.{k}")
    if not isinstance(st["drop_flags"], list):
        raise SchemaError(
            "stream.drop_flags is not a list. It is one boolean per block the "
            "reader saw, and it is what says whether ten drops were ten "
            "glitches or one gap."
        )
    for i, v in enumerate(st["drop_flags"]):
        if not isinstance(v, bool):
            raise SchemaError(
                f"stream.drop_flags[{i}] is {v!r}, which is not a boolean. A "
                "count in this list would be a second ledger disagreeing with "
                "the first."
            )


def _validate_scores(sc: Any) -> None:
    _need(sc, REQUIRED_SCORES, "scores")
    if _number(sc["hop_s"], "scores.hop_s") <= 0.0:
        raise SchemaError(f"scores.hop_s is {sc['hop_s']!r}.")
    for k in ("values", "labels"):
        if not isinstance(sc[k], list) or not sc[k]:
            raise SchemaError(
                f"scores.{k} is empty. A trace with no points is a plot "
                "nobody looked at, and Stage B's deliverable is that somebody "
                "did."
            )
    if len(sc["values"]) != len(sc["labels"]):
        raise SchemaError(
            f"scores.values has {len(sc['values'])} points and scores.labels "
            f"has {len(sc['labels'])}. One label per window or the confusion "
            "matrix is over two different recordings."
        )
    for i, v in enumerate(sc["values"]):
        _score(v, f"scores.values[{i}]")
    for i, v in enumerate(sc["labels"]):
        if v not in (0, 1) or isinstance(v, bool):
            raise SchemaError(
                f"scores.labels[{i}] is {v!r}; 0 or 1, as an integer. A "
                "boolean here would be a truth somebody computed from the "
                "scores rather than from the recording."
            )
    _score(sc["threshold"], "scores.threshold")


def _validate_timing(tm: Any) -> None:
    _need(tm, REQUIRED_TIMING, "timing")
    _pos_int(tm["hops"], "timing.hops")
    if _number(tm["hop_ms"], "timing.hop_ms") <= 0.0:
        raise SchemaError(
            f"timing.hop_ms is {tm['hop_ms']!r}. The hop is the budget and a "
            "budget of zero divides nothing."
        )
    for k in ("front_end_ms", "model_ms"):
        if _number(tm[k], f"timing.{k}") < 0.0:
            raise SchemaError(
                f"timing.{k} is {tm[k]}. A negative duration is two clocks, "
                "not a fast stage, and no report can be built on top of it."
            )


def _validate_quiet(q: Any) -> None:
    _need(q, REQUIRED_QUIET, "quiet")
    if _number(q["seconds"], "quiet.seconds") <= 0.0:
        raise SchemaError(
            f"quiet.seconds is {q['seconds']!r}. A count of false triggers "
            "with no duration under it is not a rate, and the whole of "
            "Stage D is the difference."
        )
    for k in ("false_triggers", "smoothed_false_triggers"):
        _count(q[k], f"quiet.{k}")
    _score(q["threshold"], "quiet.threshold")
    for k in ("recall_before", "recall_after"):
        if q[k] is not None:
            _score(q[k], f"quiet.{k}")


def _validate_events(ev: Any) -> None:
    _need(ev, REQUIRED_EVENTS, "events")
    if _number(ev["collar_s"], "events.collar_s") < 0.0:
        raise SchemaError(f"events.collar_s is {ev['collar_s']!r}.")
    for k in ("predicted_s", "truth_s"):
        if not isinstance(ev[k], list):
            raise SchemaError(f"events.{k} is not a list.")
        last = None
        for i, v in enumerate(ev[k]):
            t = _number(v, f"events.{k}[{i}]")
            if t < 0.0:
                raise SchemaError(
                    f"events.{k}[{i}] is {t}. An onset is seconds from the "
                    "start of the stream and a stream does not start before "
                    "it starts."
                )
            if last is not None and t < last:
                raise SchemaError(
                    f"events.{k}[{i}] is {t} after {last}. Onsets are in "
                    "order; a list that is not sorted was matched by "
                    "position somewhere upstream."
                )
            last = t
    if not ev["truth_s"]:
        raise SchemaError(
            "events.truth_s is empty. A recall over no events is 1.0 by "
            "arithmetic and says nothing, which is the worst of the outcomes "
            "because it looks like the best."
        )
    if not isinstance(ev["log"], list):
        raise SchemaError("events.log is not a list.")
    for i, row in enumerate(ev["log"]):
        _need(row, ("onset_s", "score", "windows"), f"events.log[{i}]")


def validate(doc: Any) -> None:
    """Raise `SchemaError` unless `doc` is a Lab 11 report."""
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