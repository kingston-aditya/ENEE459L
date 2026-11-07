from __future__ import annotations

from typing import Any, Iterable, Sequence

from schema import BLACK_MAX, FLAT_SPREAD

import cv2
import shutil
import time
import json
import numpy as np
from pathlib import Path

class FrameError(ValueError):
    """A shape or a format this module cannot price. `capture.py` exits 3."""


# The formats this lab prices, in the order Lecture 07 slide 27 lists them.
# Written as a tuple rather than derived from the function below, because
# `_bytes_per_pixel` is stubbed in the student tree and a starter whose
# FORMATS list was empty until the stub was filled would fail in a way that
# points at the wrong line.
FORMATS: tuple[str, ...] = ("raw10", "gray8", "nv12", "i420", "rgb", "bgr",
                            "bgrx")

# What each format is, in one clause, for the summary table and the error
# message. Not used by any arithmetic.
FORMAT_NOTES: dict[str, str] = {
    "raw10": "on the CSI wire, four pixels packed into five bytes, no ISP yet",
    "gray8": "luma only, which is a decision about colour and not a format",
    "nv12": "luma full, chroma quartered and interleaved -- the ISP's output",
    "i420": "the same bytes as NV12 with the two chroma planes kept apart",
    "rgb": "three bytes, nothing shared, nothing wasted",
    "bgr": "the same three bytes, ordered the way OpenCV expects them",
    "bgrx": "four bytes, one of which nobody reads, bought for alignment",
}


def _bytes_per_pixel(fmt: str) -> float:
    table = {
        # One byte of luma per pixel, plus a quarter of a byte of Cb and a
        # quarter of a byte of Cr, because the chroma plane is half width and
        # half height. NV12 interleaves the two chroma channels in one plane
        # and I420 keeps them in two, which changes the layout and not the
        # total, which is why both entries are the same number.
        "nv12": 1.5,
        "i420": 1.5,
        # Ten bits per pixel on the wire: four pixels in five bytes. This is
        # the only entry describing something that has not reached memory yet.
        "raw10": 1.25,
        "gray8": 1.0,
        "rgb": 3.0,
        "bgr": 3.0,
        # The fourth byte is padding. It carries no information and it costs
        # exactly as much to move as the three that do.
        "bgrx": 4.0,
    }
    key = str(fmt).lower()
    if key not in table:
        raise FrameError(
            f"format {fmt!r} is not one of {', '.join(FORMATS)}. If you meant "
            "a format this lab does not price, add it here and say in your "
            "paragraph what its bytes per pixel is and how you know."
        )
    return table[key]



# ---------------------------------------------------------------------------
# Hardware Capture & Pipeline Configuration
# ---------------------------------------------------------------------------

def gstreamer_pipeline(
    capture_width: int = 1920,
    capture_height: int = 1080,
    display_width: int = 1920,
    display_height: int = 1080,
    framerate: int = 30,
    flip_method: int = 0,
) -> str:
    return (
        f"nvarguscamerasrc ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! "
        f"appsink drop=1"
    )


def grab_frame(pipeline: str, warmup_frames: int = 15) -> np.ndarray:
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        raise RuntimeError("Failed to open camera via GStreamer pipeline.")

    try:
        # Warmup loop to allow sensor auto-exposure and AWB to converge
        for _ in range(warmup_frames):
            ret, _ = cap.read()
            if not ret:
                time.sleep(0.03)

        ret, frame = cap.read()
        if not ret or frame is None:
            raise RuntimeError("Camera opened, but failed to capture a valid frame.")
        return frame
    finally:
        cap.release()


############################
## Your work starts here ###
############################

def frame_bytes(width: int, height: int, fmt: str) -> int:
    # round, not truncate: 1.25 and 1.5 are exact in binary, but a product
    # that lands a hair under an integer must still count as that integer.
    return int(round(width * height * _bytes_per_pixel(fmt)))


def bytes_per_second(width: int, height: int, fmt: str, fps: float) -> float:
    return float(frame_bytes(width, height, fmt) * fps)


def frame_stats(pixels: Sequence[float] | Iterable[float]) -> dict[str, float]:
    if isinstance(pixels, np.ndarray):
        values = np.asarray(pixels, dtype=np.float64).ravel()
    elif isinstance(pixels, Sequence) and not isinstance(pixels, (str, bytes)):
        values = np.asarray(pixels, dtype=np.float64).ravel()
    else:
        values = np.fromiter(pixels, dtype=np.float64)
    if values.size == 0:
        raise FrameError("frame_stats needs at least one pixel")
    lowest = float(values.min())
    highest = float(values.max())
    mean = float(values.mean())
    # The frame is the whole population, so the divisor is N, not N-1.
    sd = float(values.std(ddof=0))
    return {
        "min": lowest,
        "max": highest,
        "mean": mean,
        "spread": highest - lowest,
        "sd": sd,
        "samples": float(values.size),
    }


def classify(stats: dict[str, float]) -> tuple[str, str]:
    mean = float(stats["mean"])
    spread = float(stats["spread"])
    maximum = float(stats["max"])
    detail = f"mean {mean:.4f}, spread {spread:.4f}"
    # Silence first: a dead sensor is not a dark picture. One count in 255
    # is the smallest thing an 8-bit frame can say.
    if maximum <= BLACK_MAX:
        return ("black", f"{detail}. Dead sensor, no signal.")
    # Signal with no structure: a stuck test pattern or a flat field.
    if spread < FLAT_SPREAD:
        return ("flat", f"{detail}. Featureless flat field.")
    # A real scene that never climbed out of the bottom tenth of the scale.
    if mean < 0.10:
        return ("underexposed", f"{detail}. Underexposed room.")
    return ("scene", f"{detail}. Exposed and structured.")


def conversion_bytes(width: int, height: int, src: str, dst: str) -> int:
    # The bus reads every source byte and writes every destination byte.
    return frame_bytes(width, height, src) + frame_bytes(width, height, dst)


def resize_bytes(src_w: int, src_h: int, dst_w: int, dst_h: int,
                 fmt: str) -> int:
    return frame_bytes(src_w, src_h, fmt) + frame_bytes(dst_w, dst_h, fmt)


def normalise_bytes(width: int, height: int, channels: int = 3,
                    out_bytes: int = 4) -> int:
    # Read the integer pixels, write the wider tensor. The input element is
    # one byte; out_bytes is the element width of the float tensor.
    pixels = width * height * channels
    return pixels * (1 + out_bytes)


def summarise_formats(width: int, height: int) -> list[dict[str, Any]]:
    rgb_bytes = frame_bytes(width, height, "rgb")
    rows: list[dict[str, Any]] = []
    for fmt in FORMATS:
        nbytes = frame_bytes(width, height, fmt)
        rows.append({
            "format": fmt,
            "bytes_per_pixel": _bytes_per_pixel(fmt),
            "bytes": nbytes,
            "relative_to_rgb": nbytes / rgb_bytes,
            "note": FORMAT_NOTES[fmt],
        })
    return rows


###############################
##### The main function #######
###############################
def main(
    output_dir: str = "output",
    image_filename: str = "captured_frame.jpg",
    json_filename: str = "frame_report.json",
    target_fps: float = 30.0,
    source_image: str | None = None,
) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    img_path = out_path / image_filename
    json_path = out_path / json_filename

    # 1. Capture frame from hardware, or price a frame already on disk.
    if source_image:
        frame_bgr = cv2.imread(source_image)
        if frame_bgr is None:
            raise RuntimeError(f"Could not read image {source_image}")
        shutil.copyfile(source_image, img_path)
    else:
        pipeline_str = gstreamer_pipeline()
        frame_bgr = grab_frame(pipeline_str)
        cv2.imwrite(str(img_path), frame_bgr)
    height, width, _ = frame_bgr.shape

    # 3. Extract normalized luma/grayscale values in [0.0, 1.0] for classification
    # classify() tests against BLACK_MAX (1/255 ≈ 0.0039) and mean < 0.10
    gray_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    normalized_luma = gray_frame.astype(np.float32).ravel() / 255.0

    # 4. Compute statistics and scene category
    stats = frame_stats(normalized_luma)
    classification, reason = classify(stats)

    # 5. Calculate memory bus bandwidth and conversion costs
    formats_table = summarise_formats(width, height)
    bgr_bandwidth_bps = bytes_per_second(width, height, "bgr", target_fps)
    nv12_to_bgr_cost = conversion_bytes(width, height, "nv12", "bgr")
    norm_cost = normalise_bytes(width, height, channels=3, out_bytes=4)

    # Downsampling budget example (1080p -> 224x224 input tensor)
    resize_cost = resize_bytes(width, height, 224, 224, "rgb")

    # 6. Aggregate payload and write JSON
    payload: dict[str, Any] = {
        "capture_metadata": {
            "saved_image_path": str(img_path.resolve()),
            "width": width,
            "height": height,
            "channels": 3,
            "assumed_fps": target_fps,
        },
        "frame_analysis": {
            "classification": classification,
            "classification_reason": reason,
            "stats": stats,
        },
        "memory_pricing": {
            "bandwidth_bytes_per_sec": {
                "bgr_live_stream": bgr_bandwidth_bps,
                "nv12_live_stream": bytes_per_second(width, height, "nv12", target_fps),
            },
            "format_comparison": formats_table,
            "pipeline_stage_costs": {
                "nv12_to_bgr_conversion_bytes": nv12_to_bgr_cost,
                "resize_to_224x224_rgb_bytes": resize_cost,
                "fp32_normalization_tensor_bytes": norm_cost,
            },
        },
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    print(f"Captured frame saved to : {img_path}")
    print(f"Analysis saved to       : {json_path}")
    print(f"Classification result   : {classification.upper()} ({reason})")

if __name__ == "__main__":
    main()