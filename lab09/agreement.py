
from __future__ import annotations

from typing import Any, Iterable, Sequence

from schema import LATENCY_PERCENTILES, REL_FLOOR

import json
from pathlib import Path

########################################################
##########   Helper functions         ##################
########################################################


def deviation_sentence(abs_res: dict[str, Any], rel_res: dict[str, Any]) -> str:
    """The two deviation metrics in one line, with the caveat. Provided complete.

    Read it before writing `max_rel_dev`. The clause after the semicolon is the
    honest disclosure and it appears whenever any denominator was floored --
    which, on a classification head, is almost always.
    """
    line = (f"max |a-b| = {abs_res['max_abs']:.6g} at index {abs_res['index']}; "
            f"max relative = {rel_res['max_rel']:.6g}")
    if rel_res["floored"]:
        line += (f" (denominator floored on {rel_res['floored']} of "
                 f"{rel_res['n']} entries; smallest |b| was "
                 f"{rel_res['denom_min']:.3g})")
    return line


def decision_sentence(dm: dict[str, Any], tol: float) -> str:
    """The claim `decision_margin` licenses, or the one it refuses. Provided."""
    if dm["safe"]:
        return (f"no decision flips: the smallest margin over {dm['n']} inputs "
                f"is {dm['min']:.6g} and the deviation is {tol:.6g}")
    return (f"{dm['below_tol']} of {dm['n']} decisions sit inside the "
            f"deviation: smallest margin {dm['min']:.6g} at row {dm['argmin']} "
            f"against a deviation of {tol:.6g}")


class AgreementError(ValueError):
    """A comparison this module cannot make. `engine.py` exits 3."""


def _finite(v: Any, where: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise AgreementError(f"{where} is {v!r}, which is not a number.")
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):
        raise AgreementError(
            f"{where} is {f}. A NaN or an infinity in an output array is the "
            "run failing quietly; it is not a value to take a maximum over."
        )
    return f


def _percentile(xs: Sequence[float], q: float) -> float:
    """Linear interpolation between the two nearest ranks. Provided complete.

    The same implementation Labs 04 through 08 use, here for the same reason:
    a lab whose percentile is nearest-rank and a lab whose percentile
    interpolates produce different p95s from the same samples, and a student
    comparing this week's table against last week's should be comparing the
    board and not the arithmetic.
    """
    s = sorted(float(x) for x in xs)
    if not s:
        raise AgreementError("no samples.")
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * (float(q) / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac


########################################################
##########    Start from here          #################
########################################################


def latency_report(ms: Iterable[float]) -> dict[str, Any]:
    samples = [_finite(v, "duration") for v in ms]
    for v in samples:
        if v < 0.0:
            raise AgreementError(
                f"duration is {v}. A negative duration is two clocks, "
                "not a fast backend."
            )
    if not samples:
        raise AgreementError("no samples.")
    n = len(samples)
    percentiles = {q: _percentile(samples, q) for q in LATENCY_PERCENTILES}
    p50 = percentiles[50]
    p95 = percentiles[95]
    p99 = percentiles[99]
    return {
        "n": n,
        "mean": sum(samples) / n,
        "worst": max(samples),
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "jitter": p95 - p50,
    }


def speedup(base_ms: float, other_ms: float) -> dict[str, Any]:
    base = _finite(base_ms, "base_ms")
    other = _finite(other_ms, "other_ms")
    if base < 0.0 or other <= 0.0:
        raise AgreementError(
            f"base_ms is {base} and other_ms is {other}. "
            "A speedup needs a non-negative baseline and a positive comparison."
        )
    factor = base / other
    return {
        "factor": factor,
        "faster": factor > 1.0,
        "saved_ms": base - other,
    }


def max_abs_dev(a: Sequence[float], b: Sequence[float]) -> dict[str, Any]:
    if len(a) != len(b):
        raise AgreementError(
            f"sequences have lengths {len(a)} and {len(b)}."
        )
    if not a:
        raise AgreementError("no samples.")
    best_abs = None
    best_index = 0
    best_a = 0.0
    best_b = 0.0
    for i, (left, right) in enumerate(zip(a, b)):
        av = _finite(left, f"a[{i}]")
        bv = _finite(right, f"b[{i}]")
        dev = abs(av - bv)
        if best_abs is None or dev > best_abs:
            best_abs = dev
            best_index = i
            best_a = av
            best_b = bv
    return {
        "max_abs": best_abs,
        "index": best_index,
        "a": best_a,
        "b": best_b,
        "n": len(a),
    }


def max_rel_dev(a: Sequence[float], b: Sequence[float],
                floor: float = REL_FLOOR) -> dict[str, Any]:
    floor_v = _finite(floor, "floor")
    if floor_v <= 0.0:
        raise AgreementError(
            f"floor is {floor_v}. A relative-error floor has to be strictly positive."
        )
    if len(a) != len(b):
        raise AgreementError(
            f"sequences have lengths {len(a)} and {len(b)}."
        )
    if not a:
        raise AgreementError("no samples.")
    best_rel = None
    best_index = 0
    floored = 0
    denom_min = None
    for i, (left, right) in enumerate(zip(a, b)):
        av = _finite(left, f"a[{i}]")
        bv = _finite(right, f"b[{i}]")
        mag = abs(bv)
        if denom_min is None or mag < denom_min:
            denom_min = mag
        if mag < floor_v:
            floored += 1
        rel = abs(av - bv) / max(mag, floor_v)
        if best_rel is None or rel > best_rel:
            best_rel = rel
            best_index = i
    return {
        "max_rel": best_rel,
        "index": best_index,
        "floored": floored,
        "denom_min": denom_min,
        "n": len(a),
    }


def top1_agreement(rows_a: Sequence[Sequence[float]],
                   rows_b: Sequence[Sequence[float]]) -> dict[str, Any]:
    if len(rows_a) != len(rows_b):
        raise AgreementError(
            f"batches have lengths {len(rows_a)} and {len(rows_b)}."
        )
    if not rows_a:
        raise AgreementError("no samples.")

    def argmax(row: Sequence[float], where: str) -> int:
        if not row:
            raise AgreementError(f"{where} is empty.")
        best_i = 0
        best_v = _finite(row[0], f"{where}[0]")
        for j, value in enumerate(row):
            fv = _finite(value, f"{where}[{j}]")
            if fv > best_v:
                best_v = fv
                best_i = j
        return best_i

    agree = 0
    first = None
    for i, (ra, rb) in enumerate(zip(rows_a, rows_b)):
        if len(ra) != len(rb):
            raise AgreementError(
                f"row {i} has lengths {len(ra)} and {len(rb)}."
            )
        if argmax(ra, f"rows_a[{i}]") == argmax(rb, f"rows_b[{i}]"):
            agree += 1
        elif first is None:
            first = i
    n = len(rows_a)
    return {
        "n": n,
        "agree": agree,
        "disagree": n - agree,
        "rate": agree / n,
        "first_disagreement": first,
    }


def decision_margin(rows: Sequence[Sequence[float]],
                    tol: float) -> dict[str, Any]:
    tolerance = _finite(tol, "tol")
    if tolerance < 0.0:
        raise AgreementError(
            f"tol is {tolerance}. A deviation tolerance cannot be negative."
        )
    if not rows:
        raise AgreementError("no samples.")
    margins: list[float] = []
    for r, row in enumerate(rows):
        if len(row) < 2:
            raise AgreementError(
                f"row {r} has {len(row)} classes. A margin needs a runner-up."
            )
        values = [_finite(v, f"rows[{r}][{i}]") for i, v in enumerate(row)]
        order = sorted(range(len(values)), key=lambda i: (-values[i], i))
        margins.append(values[order[0]] - values[order[1]])
    min_margin = margins[0]
    argmin = 0
    for i, margin in enumerate(margins):
        if margin < min_margin:
            min_margin = margin
            argmin = i
    below = sum(1 for margin in margins if margin < tolerance)
    return {
        "n": len(rows),
        "min": min_margin,
        "median": _percentile(margins, 50),
        "mean": sum(margins) / len(margins),
        "argmin": argmin,
        "below_tol": below,
        "safe": below == 0,
    }

#############################################################
###############  Main function starts here ##################
#############################################################

def main(
    input_path: str | Path = "benchmark_input_data.json",
    output_path: str | Path = "benchmark_results.json",
) -> None:
    in_file = Path(input_path)
    out_file = Path(output_path)

    # 1. Load synthetic data from JSON
    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file.resolve()}")

    with in_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    timings_base = data["timings_base"]
    timings_optimized = data["timings_optimized"]
    flat_logits_base = data["flat_logits_base"]
    flat_logits_opt = data["flat_logits_opt"]
    batched_scores_base = data["batched_scores_base"]
    batched_scores_opt = data["batched_scores_opt"]

    # 2. Execute metric and report functions
    report_base = latency_report(timings_base)
    report_opt = latency_report(timings_optimized)
    perf_speedup = speedup(base_ms=report_base["p50"], other_ms=report_opt["p50"])

    abs_dev = max_abs_dev(flat_logits_opt, flat_logits_base)
    rel_dev = max_rel_dev(flat_logits_opt, flat_logits_base, floor=REL_FLOOR)

    agreement = top1_agreement(batched_scores_opt, batched_scores_base)
    margin = decision_margin(batched_scores_base, tol=abs_dev["max_abs"])

    # 3. Structure output results
    results: dict[str, Any] = {
        "latency": {
            "base": report_base,
            "optimized": report_opt,
            "speedup_p50": perf_speedup,
        },
        "deviations": {
            "max_abs_dev": abs_dev,
            "max_rel_dev": rel_dev,
            "summary_sentence": deviation_sentence(abs_dev, rel_dev),
        },
        "agreement": {
            "top1_agreement": agreement,
            "decision_margin": margin,
            "decision_sentence": decision_sentence(margin, tol=abs_dev["max_abs"]),
        },
    }

    # 4. Save results to JSON
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # 5. Print a console summary
    print(f"Loaded input from: {in_file.resolve()}")
    print(f"Results saved to:  {out_file.resolve()}\n")
    print("--- Summary ---")
    print(results["deviations"]["summary_sentence"])
    print(results["agreement"]["decision_sentence"])
    print(
        f"Speedup (p50): {perf_speedup['factor']:.2f}x "
        f"({perf_speedup['saved_ms']:.2f} ms saved)"
    )

if __name__ == "__main__":
    main()