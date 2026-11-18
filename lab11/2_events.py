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


class EventError(ValueError):
    """An argument this module refuses to do arithmetic on."""


def _flags(seq, what: str) -> list:
    out = []
    for i, v in enumerate(seq):
        if not isinstance(v, bool):
            raise EventError(f"{what}[{i}] is {v!r}, which is not a boolean.")
        out.append(v)
    return out


def _times(seq, what: str) -> list:
    out = []
    last = None
    for i, v in enumerate(seq):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EventError(f"{what}[{i}] is {v!r}, which is not a number.")
        t = float(v)
        if t < 0.0:
            raise EventError(
                f"{what}[{i}] is {t}. An onset is seconds from the start of "
                "the stream."
            )
        if last is not None and t < last:
            raise EventError(
                f"{what} is not sorted: {t} follows {last}. Every matcher in "
                "this module walks the two lists in order."
            )
        last = t
        out.append(t)
    return out


def _scores(seq, what: str) -> list:
    """Scores in [0, 1], or a refusal that says what the number probably is.

    The same check `decide._score_list` makes, duplicated here rather than
    imported so that `events.py` stays a leaf: a student who breaks
    `decide.py` should not find `hysteresis` broken too.
    """
    out = []
    for i, v in enumerate(seq):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EventError(f"{what}[{i}] is {v!r}, which is not a number.")
        f = float(v)
        if f < 0.0 or f > 1.0:
            raise EventError(
                f"{what}[{i}] is {f}. Scores here are in [0, 1]; a value "
                "outside it is a logit or a percentage, and both look like a "
                "confident model from here."
            )
        out.append(f)
    return out


def rising_edges(flags) -> list:
    """The index of every position where a run of trues begins.

    Position 0 counts as a rising edge if it is true. A stream that starts
    mid-word did start mid-word, and refusing to call that an onset loses the
    first event of every recording that was not started in silence.
    """
    seq = _flags(flags, "flags")
    out = []
    prev = False
    for i, v in enumerate(seq):
        if v and not prev:
            out.append(i)
        prev = v
    return out





def onsets_seconds(indices, hop_s: float) -> list:
    """Window indices to seconds. `index * hop_s`, and nothing else.

    Not `(index + 0.5) * hop_s` and not `index * hop_s + window_s`. The onset
    of a window is where the window starts, the collar absorbs the rest, and a
    module that adds half a hop here and a collar that was sized against the
    ladder are two corrections for one problem.
    """
    hop = float(hop_s)
    if hop <= 0.0:
        raise EventError(f"hop_s is {hop_s!r}.")
    out = []
    for i, v in enumerate(indices):
        if isinstance(v, bool) or not isinstance(v, int):
            raise EventError(f"indices[{i}] is {v!r}, which is not an index.")
        if v < 0:
            raise EventError(f"indices[{i}] is {v}.")
        out.append(v * hop)
    return out


def at_least_k(k: int, m: int, p: float) -> float:
    """The chance that at least `k` of `m` independent windows fire, each with
    probability `p`.

    The binomial tail, summed from `k` up. `at_least_k(3, 4, 0.95)` is
    0.98598, which is the number that says a 3-of-5 rule applied to a word
    occupying four positive windows *raises* word recall above the 0.95 window
    recall it is built from.

    Two warnings that belong on the answer whenever it is quoted.
    Independence is the assumption and it is false: consecutive windows share
    ninety per cent of their audio and their errors are correlated, so the
    real number is lower. And `m` is how many positive windows the word
    occupies, which is not `n` -- a 3-of-5 rule over a four-window word is
    asking for 3 of 4, and writing 3-of-5 next to a figure labelled 3 of 4
    reads as a typo when both are true.

    `k > m` is refused rather than answered with 0.0. It is arithmetically
    zero and it is almost always the `m`-is-not-`n` confusion above, so the
    zero would be a correct answer to a question the caller did not mean to
    ask.
    """
    kk, mm = int(k), int(m)
    if mm < 0:
        raise EventError(f"m is {m!r}.")
    if kk < 0:
        raise EventError(f"k is {k!r}.")
    q = float(p)
    if q < 0.0 or q > 1.0:
        raise EventError(f"p is {q}; a probability is in [0, 1].")
    if kk > mm:
        raise EventError(
            f"at_least_k({kk}, {mm}, ...): you cannot have {kk} of {mm}. If "
            f"{mm} is the vote's window `n`, it is the wrong argument -- `m` "
            "is how many positive windows the word occupies."
        )
    total = 0.0
    for i in range(kk, mm + 1):
        total += math.comb(mm, i) * (q ** i) * ((1.0 - q) ** (mm - i))
    return total


def event_latency(match: dict) -> dict:
    """How late the hits were, in milliseconds.

    Four keys: count, mean_ms, median_ms, worst_ms. The three millisecond
    keys are None when nothing matched; `count` is 0 and never None, because
    a caller summing counts across sessions should not have to special-case
    the empty one.

    `worst_ms` is the maximum of the *signed* deltas and not of their absolute
    values. A prediction 50 ms early and one 600 ms late are not equally
    wrong; the second is the one that has to fit under the ladder.
    """
    deltas = [float(m["delta_s"]) * 1000.0 for m in match["matches"]]
    if not deltas:
        return {"count": 0, "mean_ms": None, "median_ms": None,
                "worst_ms": None}
    ordered = sorted(deltas)
    mid = len(ordered) // 2
    median = (ordered[mid] if len(ordered) % 2
              else (ordered[mid - 1] + ordered[mid]) / 2.0)
    return {
        "count": len(deltas),
        "mean_ms": sum(deltas) / len(deltas),
        "median_ms": median,
        "worst_ms": max(deltas),
    }


def event_rates(match: dict, seconds: float) -> dict:
    """Recall, and false alarms in the unit an argument happens in.

    Four keys: recall, false_alarms, false_alarms_per_hour, seconds.

    `recall` is hits over hits plus misses, and is None when there were no
    truth events -- a recall of 1.0 over nothing is the most misleading number
    this module could return.
    """
    s = float(seconds)
    if s <= 0.0:
        raise EventError(
            f"seconds is {seconds!r}. A count of false alarms with no "
            "duration under it is not a rate."
        )
    hits = int(match["hits"])
    misses = int(match["misses"])
    fa = int(match["false_alarms"])
    total = hits + misses
    return {
        "recall": (hits / total) if total else None,
        "false_alarms": fa,
        "false_alarms_per_hour": fa * SECONDS_PER_HOUR / s,
        "seconds": s,
    }


def smoothing_trade(before: dict, after: dict, vote_ms: float) -> dict:
    """Both halves of what smoothing did, and neither of them alone.

    Six keys: rate_before, rate_after, rate_factor, recall_before,
    recall_after, latency_ms.

    `rate_factor` is before over after and is None when after is zero, for the
    same reason `rate_change` in `decide.py` returns None there: an infinite
    improvement is a measurement that ran out of events.

    `latency_ms` is the price, and it is passed in rather than derived because
    it comes from the ladder and the ladder knows the hop. This is the key
    that makes the return a trade rather than a result. A report that carries
    the two rates and not this one is a report claiming smoothing was free.
    """
    rb = before.get("false_alarms_per_hour")
    ra = after.get("false_alarms_per_hour")
    if rb is None or ra is None:
        raise EventError(
            "a trade needs a false-alarm rate on both sides. One of them is "
            "missing, which means one half was never measured."
        )
    v = float(vote_ms)
    if v < 0.0:
        raise EventError(f"vote_ms is {v}.")
    return {
        "rate_before": float(rb),
        "rate_after": float(ra),
        "rate_factor": None if ra <= 0.0 else float(rb) / float(ra),
        "recall_before": before.get("recall"),
        "recall_after": after.get("recall"),
        "latency_ms": v,
    }


def build_log(indices, values, hop_s: float, n: int) -> list:
    """One row per accepted onset: the row Stage E hands in.

    Each row has onset_s, index, score and windows.

    `score` is the highest score in the `n` windows ending at the onset, not
    the score at the onset itself. The onset is where the vote crossed, which
    is by construction not where the model was most confident, and a log that
    printed the crossing score would make every event look marginal.

    `windows` is how many of those `n` were above nothing at all -- it is
    `n` clipped to the start of the stream -- and it is in the row so that the
    first event of a recording is visibly scored over fewer windows than the
    rest.
    """
    hop = float(hop_s)
    if hop <= 0.0:
        raise EventError(f"hop_s is {hop_s!r}.")
    nn = int(n)
    if nn < 1:
        raise EventError(f"n is {n!r}.")
    vals = [float(v) for v in values]
    out = []
    for idx in indices:
        i = int(idx)
        if i < 0 or i >= len(vals):
            raise EventError(
                f"onset index {i} is outside a trace of {len(vals)} windows.")
        lo = max(0, i - nn + 1)
        out.append({
            "onset_s": i * hop,
            "index": i,
            "score": max(vals[lo:i + 1]),
            "windows": i + 1 - lo,
        })
    return out


# --- provided complete: the sentences Stage E hands in ----------------------


def match_sentence(match: dict, rates: dict) -> str:
    """One line for the matcher. Provided; read it for the key names."""
    recall = "no truth events" if rates["recall"] is None \
        else f"recall {rates['recall']:.3f}"
    return (f"{match['hits']} hits, {match['misses']} misses and "
            f"{match['false_alarms']} false alarms under a "
            f"{match['collar_s'] * 1000:.0f} ms collar; {recall}")


def latency_sentence(lat: dict) -> str:
    """One line for the latencies. Provided; note which field it leads on."""
    if lat["count"] == 0:
        return "nothing matched, so there is no latency to report"
    return (f"{lat['count']} hits, worst {lat['worst_ms']:.0f} ms, median "
            f"{lat['median_ms']:.0f} ms, mean {lat['mean_ms']:.0f} ms")


def trade_sentence(trade: dict) -> str:
    """One line for the trade. Provided; it refuses to print one half alone."""
    head = (f"{trade['rate_before']:.1f} false alarms an hour became "
            f"{trade['rate_after']:.1f}")
    if trade["rate_factor"] is not None:
        head += f", a factor of {trade['rate_factor']:.2f}"
    rb, ra = trade["recall_before"], trade["recall_after"]
    if rb is None or ra is None:
        return head + ", and the recall it cost was not measured"
    moved = "cost" if ra < rb else "gained"
    return (head + f"; recall {rb:.3f} to {ra:.3f}, so the vote {moved} "
            f"{abs(ra - rb):.3f} of it and {trade['latency_ms']:.0f} ms of "
            "latency")


#######################################################
######## Students start editing here ##################
#######################################################

def k_of_n(flags, k: int, n: int) -> list:
    pass

def hysteresis(values, enter: float, leave: float) -> list:
    pass

def match_events(predicted_s, truth_s, collar_s: float) -> dict:
    pass

def refractory(flags, hop_s: float, refractory_s: float) -> list:
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
        raise EventError(
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
        description="Run Stage E event smoothing & matching on a .wav file and output a Lab 11 session JSON."
    )
    parser.add_argument("wav_file", type=Path, help="Path to input 16-bit PCM .wav file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("events_session.json"),
        help="Path to output JSON file (default: events_session.json)",
    )
    parser.add_argument("--hop-s", type=float, default=0.1, help="Hop in seconds (default: 0.1)")
    parser.add_argument("--window-s", type=float, default=1.0, help="Window in seconds (default: 1.0)")
    parser.add_argument("--enter", type=float, default=0.6, help="Hysteresis enter threshold (default: 0.6)")
    parser.add_argument("--leave", type=float, default=0.4, help="Hysteresis leave threshold (default: 0.4)")
    parser.add_argument("--k", type=int, default=3, help="Vote k in k-of-n (default: 3)")
    parser.add_argument("--n", type=int, default=5, help="Vote n in k-of-n (default: 5)")
    parser.add_argument("--refractory-s", type=float, default=1.0, help="Refractory mute in seconds (default: 1.0)")
    parser.add_argument("--collar-s", type=float, default=0.5, help="Matching collar in seconds (default: 0.5)")
    args = parser.parse_args()

    if not args.wav_file.is_file():
        print(f"Error: File not found: {args.wav_file}", file=sys.stderr)
        return EXIT_FAILED

    try:
        audio_meta, scores = _extract_audio_and_scores(
            args.wav_file, args.window_s, args.hop_s
        )
        duration_s = audio_meta["seconds"]

        # Raw (unsmoothed) single-threshold flags vs. smoothed (hysteresis + k-of-n + refractory)
        raw_flags = [s >= args.enter for s in scores]
        raw_indices = rising_edges(raw_flags)
        raw_onsets_s = onsets_seconds(raw_indices, args.hop_s)

        hyst_flags = hysteresis(scores, args.enter, args.leave)
        voted_flags = k_of_n(hyst_flags, args.k, args.n)
        accepted_indices = refractory(voted_flags, args.hop_s, args.refractory_s)
        predicted_s = onsets_seconds(accepted_indices, args.hop_s)

        # Reference truth onsets (derived from strong energy peaks; fallback to [0.0] so truth_s is non-empty)
        truth_flags = [s >= 0.75 for s in scores]
        truth_indices = refractory(truth_flags, args.hop_s, args.refractory_s)
        truth_s = onsets_seconds(truth_indices, args.hop_s) or [0.0]

        match_before = match_events(raw_onsets_s, truth_s, args.collar_s)
        rates_before = event_rates(match_before, duration_s)

        match_after = match_events(predicted_s, truth_s, args.collar_s)
        rates_after = event_rates(match_after, duration_s)
        lat_after = event_latency(match_after)

        vote_ms = (args.k - 1) * args.hop_s * 1000.0
        trade = smoothing_trade(rates_before, rates_after, vote_ms)
        event_log = build_log(accepted_indices, scores, args.hop_s, args.n)

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
                "k": args.k,
                "n": args.n,
                "threshold": args.enter,
                "enter": args.enter,
                "leave": args.leave,
                "refractory_s": args.refractory_s,
                "collar_s": args.collar_s,
                "event_s": event_s,
                "infer_ms": infer_ms,
                "ft_per_hour_max": 6.0,
                "stated": {
                    "ring_ms": block_ms * ring_blocks,
                    "latency_ms": (event_s * 1000.0)
                    + (args.hop_s * 1000.0)
                    + infer_ms
                    + vote_ms,
                    "decisions_per_hour": SECONDS_PER_HOUR / args.hop_s,
                },
            },
            "stream": None,
            "scores": None,
            "timing": None,
            "quiet": None,
            "events": {
                "collar_s": args.collar_s,
                "predicted_s": predicted_s,
                "truth_s": truth_s,
                "log": event_log,
            },
            "record": {
                "match_before": match_before,
                "rates_before": rates_before,
                "match_after": match_after,
                "rates_after": rates_after,
                "latency_after": lat_after,
                "smoothing_trade": trade,
                "sentences": {
                    "match": match_sentence(match_after, rates_after),
                    "latency": latency_sentence(lat_after),
                    "trade": trade_sentence(trade),
                },
            },
        }

        validate_session(session_doc)

    except (wave.Error, EventError, SchemaError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_MALFORMED

    # Remove the four null stage keys before writing the JSON file
    null_stage_keys = {"stream", "scores", "timing", "quiet"}
    output_doc = {k: v for k, v in session_doc.items() if k not in null_stage_keys}

    args.output.write_text(json.dumps(output_doc, indent=2) + "\n", encoding="utf-8")
    print(f"Saved Stage E events session JSON to {args.output}")
    return EXIT_OK

if __name__ == "__main__":
    sys.exit(main())