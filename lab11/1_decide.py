from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

try:
    from .schema import (
        EXIT_FAILED,
        EXIT_MALFORMED,
        EXIT_OK,
        LAB,
        SCHEMA_VERSION,
        SECONDS_PER_HOUR,
        SchemaError,
        validate_session,
    )
except ImportError:
    from schema import (
        EXIT_FAILED,
        EXIT_MALFORMED,
        EXIT_OK,
        LAB,
        SCHEMA_VERSION,
        SECONDS_PER_HOUR,
        SchemaError,
        validate_session,
    )


class DecideError(ValueError):
    """An argument this module refuses to do arithmetic on."""


def _score_list(values, what: str) -> list:
    out = []
    for i, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise DecideError(f"{what}[{i}] is {v!r}, which is not a number.")
        f = float(v)
        if f < 0.0 or f > 1.0:
            raise DecideError(
                f"{what}[{i}] is {f}. Scores here are in [0, 1]; a value "
                "outside it is a logit or a percentage, and both look like a "
                "confident model from here."
            )
        out.append(f)
    if not out:
        raise DecideError(f"{what} is empty.")
    return out


def _check_score(v: float, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise DecideError(f"{what} is {v!r}, which is not a number.")
    f = float(v)
    if f < 0.0 or f > 1.0:
        raise DecideError(f"{what} is {f}; must be in [0, 1].")
    return f


def _check_pos(v: float, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise DecideError(f"{what} is {v!r}; must be > 0.")
    return float(v)


def apply_threshold(values, threshold: float) -> list:
    """One boolean per score. `score >= threshold`, not `>`."""
    scores = _score_list(values, "values")
    t = _check_score(threshold, "threshold")
    return [s >= t for s in scores]


def score_span(values) -> dict:
    """Where the scores actually live, and whether a threshold is among them."""
    scores = _score_list(values, "values")
    lo = min(scores)
    hi = max(scores)
    count = len(scores)
    return {
        "min": lo,
        "max": hi,
        "span": hi - lo,
        "mean": sum(scores) / count,
        "count": count,
    }


def threshold_on_trace(values, threshold: float) -> dict:
    """Whether a threshold separates anything in the trace it was drawn on."""
    scores = _score_list(values, "values")
    t = _check_score(threshold, "threshold")
    lo = min(scores)
    hi = max(scores)
    fires = sum(1 for s in scores if s >= t)
    return {
        "threshold": t,
        "min": lo,
        "max": hi,
        "on_trace": lo <= t <= hi,
        "fires": fires,
    }

def false_triggers_per_hour(count: int, seconds: float) -> float:
    """A count over a duration, in the unit the argument happens in."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise DecideError(f"count is {count!r}; must be a non-negative integer.")
    sec = _check_pos(seconds, "seconds")
    return count * SECONDS_PER_HOUR / sec


def fpr_to_per_hour(fpr: float, hop_s: float) -> float:
    """What a false-positive rate costs once you say how often you ask."""
    f = _check_score(fpr, "fpr")
    h = _check_pos(hop_s, "hop_s")
    return f / h * SECONDS_PER_HOUR


def per_hour_to_fpr(per_hour: float, hop_s: float) -> float:
    """The inverse, and it is the one that sets a target."""
    if isinstance(per_hour, bool) or not isinstance(per_hour, (int, float)) or per_hour < 0:
        raise DecideError(f"per_hour is {per_hour!r}; must be >= 0.")
    h = _check_pos(hop_s, "hop_s")
    decisions_per_hour = SECONDS_PER_HOUR / h
    if per_hour > decisions_per_hour:
        raise DecideError(
            f"per_hour ({per_hour}) exceeds decisions per hour ({decisions_per_hour})."
        )
    return float(per_hour) * h / SECONDS_PER_HOUR


def fpr_for_precision(target: float, tpr: float, base_rate: float) -> float:
    """The false-positive rate a target precision demands."""
    tgt = _check_score(target, "target")
    if tgt <= 0.0 or tgt >= 1.0:
        raise DecideError(f"target precision {tgt} must be strictly in (0, 1).")
    t_rate = _check_score(tpr, "tpr")
    p = _check_score(base_rate, "base_rate")
    if p <= 0.0 or p >= 1.0:
        raise DecideError(f"base_rate {p} must be strictly in (0, 1).")

    return t_rate * p * (1.0 - tgt) / (tgt * (1.0 - p))


def sweep(values, labels, thresholds) -> list:
    """One row per threshold, in the order the thresholds were given."""
    rows = []
    for th in thresholds:
        cm = confusion(values, labels, th)
        rt = rates(cm)
        rows.append(
            {
                "threshold": float(th),
                "tp": cm["tp"],
                "fp": cm["fp"],
                "tn": cm["tn"],
                "fn": cm["fn"],
                "tpr": rt["tpr"],
                "fpr": rt["fpr"],
                "precision": rt["precision"],
                "recall": rt["recall"],
                "f1": rt["f1"],
            }
        )
    return rows


def operating_point(rows, hop_s: float, max_per_hour: float) -> dict | None:
    """The row with the best recall whose false-trigger rate is inside budget."""
    h = _check_pos(hop_s, "hop_s")
    if isinstance(max_per_hour, bool) or not isinstance(max_per_hour, (int, float)) or max_per_hour < 0:
        raise DecideError(f"max_per_hour is {max_per_hour!r}.")

    candidates = []
    for row in rows:
        if row["recall"] is None or row["fpr"] is None:
            continue
        ft_rate = fpr_to_per_hour(row["fpr"], h)
        if ft_rate <= max_per_hour:
            candidates.append(row)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda r: (r["recall"], -r["fpr"], r["threshold"]),
    )


def rate_change(before: int, after: int, seconds: float) -> dict:
    """What smoothing did to a count, as a rate and as a factor."""
    if isinstance(before, bool) or not isinstance(before, int) or before < 0:
        raise DecideError(f"before is {before!r}.")
    if isinstance(after, bool) or not isinstance(after, int) or after < 0:
        raise DecideError(f"after is {after!r}.")
    sec = _check_pos(seconds, "seconds")
    if after > before:
        raise DecideError(
            f"after ({after}) is greater than before ({before}); smoothing cannot invent events."
        )

    before_per_hour = false_triggers_per_hour(before, sec)
    after_per_hour = false_triggers_per_hour(after, sec)
    factor = (before / after) if after > 0 else None

    return {
        "before_per_hour": before_per_hour,
        "after_per_hour": after_per_hour,
        "factor": factor,
        "removed": before - after,
        "seconds": sec,
    }


# --- provided complete: the sentences the stages hand in ---------------------


def threshold_sentence(check: dict) -> str:
    """One line for Stage B. Provided; read it for `threshold_on_trace`'s keys."""
    if not check["on_trace"]:
        where = "above" if check["threshold"] > check["max"] else "below"
        return (f"a threshold of {check['threshold']:.3f} is {where} every "
                f"score in the trace, which runs {check['min']:.3f} to "
                f"{check['max']:.3f}; it was not chosen from this plot")
    return (f"a threshold of {check['threshold']:.3f} on a trace running "
            f"{check['min']:.3f} to {check['max']:.3f}, firing on "
            f"{check['fires']} windows")


def rate_sentence(change: dict, budget: float) -> str:
    """One line for Stage D. Provided; note that it prints both rates."""
    head = (f"{change['before_per_hour']:.1f} false triggers an hour raw, "
            f"{change['after_per_hour']:.1f} smoothed")
    if change["factor"] is not None:
        head += f", a factor of {change['factor']:.2f}"
    if change["after_per_hour"] > budget:
        return head + f" -- still over a budget of {budget:.1f} an hour"
    return head + f", inside a budget of {budget:.1f} an hour"


def base_rate_sentence(pr: dict) -> str:
    """One line for the base-rate arithmetic. Provided; it is Part 2's punchline."""
    if pr["precision"] is None:
        return "the detector fired on nothing, so precision has no value"
    return (f"a base rate of {pr['base_rate']:.3g} turns "
            f"{pr['expected_tp']:.2f} expected true firings and "
            f"{pr['expected_fp']:.2f} false ones into a precision of "
            f"{pr['precision']:.3f}")

#######################################################
######## Students start editing here ##################
#######################################################

def confusion(values, labels, threshold: float) -> dict:
    pass


def rates(cm: dict) -> dict:
    pass


def precision_at_base_rate(
    tpr: float,
    fpr: float,
    events_per_hour: int,
    positives_per_event: int,
    hop_s: float,
) -> dict:
    pass


#######################################################
######## Starting Main function #######################
#######################################################


def _extract_audio_and_scores(
    wav_path: Path, window_s: float = 1.0, hop_s: float = 0.1
) -> tuple[dict, list[float]]:
    """Extract schema-compliant audio metadata and normalized [0, 1] RMS scores."""
    sha256 = hashlib.sha256(wav_path.read_bytes()).hexdigest()

    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    if sampwidth != 2:
        raise DecideError(
            f"Expected 16-bit PCM WAV (sampwidth=2), got {sampwidth * 8}-bit."
        )

    samples = array.array("h", raw)
    if channels > 1:
        samples = samples[::channels]

    total_samples = len(samples)
    duration_s = nframes / float(sr) if sr > 0 else 0.0

    audio_meta = {
        "name": wav_path.name,
        "source": str(wav_path.resolve()),
        "sha256": sha256,
        "sample_rate": sr,
        "channels": channels,
        "bit_depth": sampwidth * 8,
        "seconds": round(duration_s, 6),
        "samples": nframes,
    }

    win_samples = max(1, int(round(window_s * sr)))
    hop_samples = max(1, int(round(hop_s * sr)))

    rms_values = []
    for start in range(0, max(1, total_samples - win_samples + 1), hop_samples):
        chunk = samples[start : start + win_samples]
        if not chunk:
            break
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        rms_values.append(rms)

    if not rms_values:
        rms_values = [0.0]

    peak = max(rms_values) or 1.0
    scores = [min(1.0, max(0.0, v / peak)) for v in rms_values]
    return audio_meta, scores


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run decide metrics on a .wav file and output a validated Lab 11 session JSON."
    )
    parser.add_argument("wav_file", type=Path, help="Path to input 16-bit PCM .wav file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("session.json"),
        help="Path to output JSON file (default: session.json)",
    )
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold in [0, 1]")
    parser.add_argument("--hop-s", type=float, default=0.1, help="Hop in seconds (default: 0.1)")
    parser.add_argument("--window-s", type=float, default=1.0, help="Window in seconds (default: 1.0)")
    args = parser.parse_args()

    if not args.wav_file.is_file():
        print(f"Error: File not found: {args.wav_file}", file=sys.stderr)
        return EXIT_FAILED

    try:
        audio_meta, scores = _extract_audio_and_scores(
            args.wav_file, args.window_s, args.hop_s
        )
        labels = [1 if s >= 0.7 else 0 for s in scores]

        span = score_span(scores)
        trace_check = threshold_on_trace(scores, args.threshold)
        cm = confusion(scores, labels, args.threshold)
        rt = rates(cm)
        thresholds = [round(i * 0.1, 2) for i in range(1, 10)]
        sweep_rows = sweep(scores, labels, thresholds)
        op_point = operating_point(sweep_rows, args.hop_s, max_per_hour=6.0)

        block_ms = 10.0
        ring_blocks = 16
        event_s = 0.5
        infer_ms = 5.0

        session_doc = {
            "schema_version": SCHEMA_VERSION,
            "lab": LAB,
            "generated": datetime.now(timezone.utc).isoformat(),
            "device_id": "local-workstation",
            "audio": audio_meta,
            "conditions": {
                "power_mode": "MAXN",
                "jetpack": "6.0",
                "trt_version": "8.6.2",
                "cuda_version": "12.2",
                "compute_capability": "8.7",
            },
            "plan": {
                "sample_rate": audio_meta["sample_rate"],
                "block_ms": block_ms,
                "ring_blocks": ring_blocks,
                "window_s": args.window_s,
                "hop_s": args.hop_s,
                "k": 3,
                "n": 5,
                "threshold": args.threshold,
                "enter": 0.6,
                "leave": 0.4,
                "refractory_s": 1.0,
                "collar_s": 0.25,
                "event_s": event_s,
                "infer_ms": infer_ms,
                "ft_per_hour_max": 6.0,
                "stated": {
                    "ring_ms": block_ms * ring_blocks,
                    "latency_ms": (event_s * 1000.0)
                    + (args.hop_s * 1000.0)
                    + infer_ms
                    + (2 * args.hop_s * 1000.0),
                    "decisions_per_hour": SECONDS_PER_HOUR / args.hop_s,
                },
            },
            "stream": None,
            "scores": {
                "hop_s": args.hop_s,
                "values": scores,
                "labels": labels,
                "threshold": args.threshold,
            },
            "timing": None,
            "quiet": None,
            "events": None,
            "record": {
                "score_span": span,
                "threshold_on_trace": trace_check,
                "confusion": cm,
                "rates": rt,
                "operating_point": op_point,
                "stage_b_sentence": threshold_sentence(trace_check),
            },
        }

        validate_session(session_doc)

    except (wave.Error, DecideError, SchemaError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_MALFORMED

    args.output.write_text(json.dumps(session_doc, indent=2) + "\n", encoding="utf-8")
    print(f"Saved validated Lab 11 session JSON to {args.output}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())