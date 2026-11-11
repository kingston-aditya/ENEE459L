from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

# If importing from .schema inside a package, keep:
# from .schema import (CLIP_RATE_MAX, DB_PER_BIT, PEAK_DBFS_MAX, PEAK_DBFS_MIN,
#                      WAV_HEADER_BYTES, CHOICES_IN_HEADER, THIRTEEN_CHOICES)
# Fallbacks provided here so the file runs standalone:
CLIP_RATE_MAX = 0.001
PEAK_DBFS_MAX = -1.0
PEAK_DBFS_MIN = -40.0
DB_PER_BIT = 6.020599913
WAV_HEADER_BYTES = 44
CHOICES_IN_HEADER = ("sample_rate", "channels", "bit_depth")
THIRTEEN_CHOICES = (
    "device_name",
    "sample_rate",
    "bit_depth",
    "channels",
    "capture_gain",
    "mic_distance_cm",
    "mic_polar_pattern",
    "room_acoustic_treatment",
    "ambient_noise_level",
    "preamp_model",
    "filter_highpass_hz",
    "target_signal_type",
    "operator_notes",
)


class CaptureError(ValueError):
    """A capture description this module refuses to do arithmetic on."""


# Helper functions
def _positive_int(v: Any, what: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise CaptureError(f"{what} is {v!r}, which is not a positive integer.")
    return v


def block_align(channels: int, bit_depth: int) -> int:
    _positive_int(channels, "channels")
    _positive_int(bit_depth, "bit_depth")
    if bit_depth % 8:
        raise CaptureError(
            f"bit_depth is {bit_depth}, which is not a whole number of bytes."
        )
    return channels * (bit_depth // 8)

def amplitude_from_dbfs(level_db: float) -> float:
    if isinstance(level_db, bool) or not isinstance(level_db, (int, float)):
        raise CaptureError(f"level_db is {level_db!r}, which is not a number.")
    return 10.0 ** (float(level_db) / 20.0)


def full_scale_range_db(bit_depth: int) -> float:
    _positive_int(bit_depth, "bit_depth")
    return bit_depth * DB_PER_BIT

def level_report(
    peak: float, rms: float, clipped: int, samples: int
) -> dict[str, Any]:
    _positive_int(samples, "samples")
    if isinstance(clipped, bool) or not isinstance(clipped, int) or clipped < 0:
        raise CaptureError(f"clipped is {clipped!r}, which is not a count.")
    if clipped > samples:
        raise CaptureError(
            f"clipped is {clipped} of {samples} samples, which is more "
            "samples than there are."
        )
    p = float(peak)
    r = float(rms)
    if r > p:
        raise CaptureError(
            f"rms {r} is above peak {p}. No signal has a root mean square "
            "above its own maximum; these were measured on different arrays."
        )
    p_db = dbfs(p)
    r_db = dbfs(r)
    crest = None if (p_db is None or r_db is None) else p_db - r_db
    rate = clipped / samples
    silent = p == 0.0
    too_hot = (
        p_db is not None and p_db > PEAK_DBFS_MAX
    ) or rate > CLIP_RATE_MAX
    too_quiet = silent or (p_db is not None and p_db < PEAK_DBFS_MIN)
    return {
        "peak": p,
        "rms": r,
        "peak_dbfs": p_db,
        "rms_dbfs": r_db,
        "crest_db": crest,
        "clipped": clipped,
        "samples": samples,
        "clip_rate": rate,
        "silent": silent,
        "too_hot": too_hot,
        "too_quiet": too_quiet,
        "usable": not (silent or too_hot or too_quiet),
    }




# Edit these
def wav_bytes(
    sample_rate: int,
    channels: int,
    bit_depth: int,
    seconds: float,
    header_bytes: int = WAV_HEADER_BYTES,
) -> dict[str, Any]:
    pass


def duration_from_bytes(
    data_bytes: int, sample_rate: int, channels: int, bit_depth: int
) -> dict[str, Any]:
    pass


def header_consistency(
    header: dict[str, Any], audio: dict[str, Any]
) -> dict[str, Any]:
    pass

def dbfs(amplitude: float) -> float | None:
    pass


def bits_in_use(peak_dbfs: float | None, bit_depth: int) -> float:
    _positive_int(bit_depth, "bit_depth")
    pass


def level_sentence(level: dict[str, Any]) -> str:
    pass


def record_gaps(record: dict[str, Any]) -> dict[str, Any]:
    pass


def record_sentence(gaps: dict[str, Any]) -> str:
    pass


# =====================================================================
# Reading the WAV file & Running the analysis
# =====================================================================

def _parse_wav(path: Path) -> tuple[dict[str, Any], bytes]:
    """Reads the bare minimum WAV header and audio body."""
    with open(path, "rb") as f:
        riff = f.read(12)
        if len(riff) < 12 or riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
            raise CaptureError(f"{path.name} is not a valid RIFF/WAVE file.")

        header: dict[str, Any] = {}
        data_bytes = b""

        # Scan chunks
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[:4]
            (chunk_size,) = struct.unpack("<I", chunk_header[4:8])

            if chunk_id == b"fmt ":
                fmt_payload = f.read(chunk_size)
                audio_format, channels, sample_rate, byte_rate, ba, bit_depth = (
                    struct.unpack("<HHIIHH", fmt_payload[:16])
                )
                header["audio_format"] = audio_format
                header["channels"] = channels
                header["sample_rate"] = sample_rate
                header["byte_rate"] = byte_rate
                header["block_align"] = ba
                header["bit_depth"] = bit_depth
                # Skip padding if chunk is padded
                if chunk_size % 2 == 1:
                    f.seek(1, 1)
            elif chunk_id == b"data":
                header["data_bytes"] = chunk_size
                data_bytes = f.read(chunk_size)
                if chunk_size % 2 == 1:
                    f.seek(1, 1)
            else:
                f.seek(chunk_size + (chunk_size % 2), 1)

    if not header or not data_bytes:
        raise CaptureError(f"Missing fmt or data chunk in {path.name}")
    return header, data_bytes


def run_analysis(
    wav_path: Path, session_audio: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Applies your module's functions to the WAV file and returns JSON-ready results."""
    header, raw_bytes = _parse_wav(wav_path)

    # 1. Stage A: Block alignment & duration consistency
    dur_info = duration_from_bytes(
        data_bytes=header["data_bytes"],
        sample_rate=header["sample_rate"],
        channels=header["channels"],
        bit_depth=header["bit_depth"],
    )

    # Header vs Session check (if session dict is provided)
    session = session_audio or {
        "sample_rate": header["sample_rate"],
        "channels": header["channels"],
        "bit_depth": header["bit_depth"],
        "seconds": dur_info["seconds"],
    }
    consistency = header_consistency(header, session)

    # Compute expected WAV size from duration
    expected_wav = wav_bytes(
        sample_rate=header["sample_rate"],
        channels=header["channels"],
        bit_depth=header["bit_depth"],
        seconds=dur_info["seconds"],
    )

    # 2. Extract amplitudes as floats in [0, 1]
    samples_count = dur_info["samples"] * header["channels"]
    bit_depth = header["bit_depth"]
    max_val = float((1 << (bit_depth - 1)) - 1)

    peak_amp = 0.0
    sum_squares = 0.0
    clipped = 0

    if bit_depth == 16:
        raw_samples = struct.unpack(f"<{samples_count}h", raw_bytes)
        for s in raw_samples:
            mag = abs(s)
            if mag >= 32767:
                clipped += 1
            if mag > peak_amp:
                peak_amp = float(mag)
            sum_squares += float(s) * float(s)
    elif bit_depth == 24:
        for i in range(0, len(raw_bytes), 3):
            s = int.from_bytes(
                raw_bytes[i : i + 3], byteorder="little", signed=True
            )
            mag = abs(s)
            if mag >= 8388607:
                clipped += 1
            if mag > peak_amp:
                peak_amp = float(mag)
            sum_squares += float(s) * float(s)
    else:
        raise CaptureError(f"Unsupported bit depth: {bit_depth}")

    norm_peak = min(1.0, peak_amp / max_val)
    norm_rms = (
        min(1.0, math.sqrt(sum_squares / samples_count) / max_val)
        if samples_count > 0
        else 0.0
    )

    # 3. Stage B: Level Report, Dynamic Range & Bits In Use
    levels = level_report(
        peak=norm_peak,
        rms=norm_rms,
        clipped=clipped,
        samples=samples_count,
    )
    actual_bits = bits_in_use(levels["peak_dbfs"], bit_depth)
    full_scale_db = full_scale_range_db(bit_depth)

    # 4. Stage E: Record completeness check
    gaps = record_gaps(session)

    # Compile essential results
    return {
        "file": str(wav_path.name),
        "header_consistency": {
            "agrees": consistency["agree"],
            "mismatches": consistency["mismatches"],
            "duration": consistency["duration"],
        },
        "wav_structure": expected_wav,
        "level_report": levels,
        "resolution": {
            "full_scale_range_db": full_scale_db,
            "bits_in_use": round(actual_bits, 3),
            "wasted_bits": round(max(0.0, bit_depth - actual_bits), 3),
        },
        "stage_e_gaps": gaps,
        "verdicts": {
            "level_sentence": level_sentence(levels),
            "record_sentence": record_sentence(gaps),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stages A, B, and E analysis on a .wav file and export to JSON."
    )
    parser.add_argument("wav_path", type=str, help="Path to input .wav file")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path for output JSON file (default: <wav_filename>_report.json)",
    )
    args = parser.parse_args()

    input_file = Path(args.wav_path)
    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_file = (
        Path(args.output)
        if args.output
        else input_file.with_name(f"{input_file.stem}_report.json")
    )

    results = run_analysis(input_file)

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)

    print(f"Results written to: {output_file}")
    print(f"Sentence: {results['verdicts']['level_sentence']}")
    print(
        f"Bits in use: {results['resolution']['bits_in_use']} of {results['wav_structure']['block_align'] * 8 // results['wav_structure']['block_align']} bits"
    )


if __name__ == "__main__":
    main()