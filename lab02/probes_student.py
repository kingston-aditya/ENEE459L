from __future__ import annotations

import json
import re
from typing import Any
import sys

from env import Env, ModuleNotAvailable, getattr_path, read_text, unknown, major_minor

# The NVIDIA-built PyTorch wheels for Jetson carry a local version segment —
# the part after "+" — that names the NVIDIA container release. A wheel from
# plain PyPI has no such segment. This is a hint, not a proof, which is why the
# probe reports the tag itself alongside the interpretation.
_NV_LOCAL_TAG = re.compile(r"(?:^|\.)nv\d", re.IGNORECASE)

# `# R36 (release), REVISION: 5.0, GCID: ...`
_L4T_RELEASE = re.compile(r"R(\d+)\s*\(release\)", re.IGNORECASE)
_L4T_REVISION = re.compile(r"REVISION:\s*([\d.]+)")

# hepler function
def _split_local_version(raw: str) -> dict[str, Any]:
    if not raw:
        return {"raw": raw, "public": None, "local": None, "nvidia_build": False}
    public, sep, local = raw.partition("+")
    local = local if sep else None
    return {
        "raw": raw,
        "public": public or None,
        "local": local,
        "nvidia_build": bool(local and _NV_LOCAL_TAG.search(local)),
    }

# ---------------------------------------------------------------------------
# The probes.
# ---------------------------------------------------------------------------

# Probe 1
def probe_torch(env: Env) -> dict[str, Any]:
    src = "import torch"
    try:
        torch = env.importer("torch")
    except ModuleNotAvailable as e:
        return unknown(src, f"torch is not importable: {e}")

    raw = getattr_path(torch, "__version__")
    version = _split_local_version(str(raw)) if raw else None

    available = getattr_path(torch, "cuda.is_available")
    cuda_available = bool(available()) if callable(available) else None

    device = None
    if cuda_available is True:
        name = getattr_path(torch, "cuda.get_device_name")
        if callable(name):
            device = name(0)

    out = {
        "value": raw,
        "source": src,
        "status": "ok" if raw else "unknown",
        "version": version,
        "cuda_available": cuda_available,
        "cuda_version": getattr_path(torch, "version.cuda"),
        "device_name": device,
    }

    if not raw:
        out["detail"] = "torch imported but exposes no __version__"
        return out

    nv = version["nvidia_build"] if version else False
    if cuda_available is True:
        out["diagnosis"] = "torch is installed and sees the GPU"
    elif cuda_available is None:
        out["diagnosis"] = "torch is installed but does not expose torch.cuda.is_available"
    elif nv is True:
        out["diagnosis"] = (
            "this is an NVIDIA build but it cannot see the GPU — the wheel is right, "
            "so look at the driver stack, the container, or the user’s groups, not at pip"
        )
    else:
        out["diagnosis"] = (
            "this wheel has no NVIDIA local version tag and cannot see the GPU — it is "
            "almost certainly a stock PyPI wheel and must be replaced from the Jetson index"
        )
    return out

# Probe 2
def probe_cuda(env: Env) -> dict[str, Any]:
    src = "/usr/local/cuda/version.json"
    raw = read_text(env.root, src)
    if not raw:
        return unknown(src, "CUDA toolkit manifest absent — no toolkit installed at /usr/local/cuda")

    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return unknown(src, "CUDA toolkit manifest is present but not valid JSON")

    version = data.get("cuda", {}).get("version")
    if not version:
        return unknown(src, "manifest present but names no cuda version")

    return {
        "value": version,
        "source": src,
        "status": "ok",
        "line": major_minor(version),
    }

# Probe 3
def probe_opencv(env: Env) -> dict[str, Any]:
    src = "import cv2"
    try:
        cv2 = env.importer("cv2")
    except ModuleNotAvailable as e:
        return unknown(src, f"cv2 is not importable: {e}")

    raw = getattr_path(cv2, "__version__")
    counter = getattr_path(cv2, "cuda.getCudaEnabledDeviceCount")
    if callable(counter):
        devices = int(counter())
        cuda_devices = devices
        if devices:
            detail = f"built with CUDA, {devices} device(s) visible"
        else:
            detail = "the cv2.cuda namespace exists but reports no devices — this is a non-CUDA build"
    else:
        cuda_devices = None
        detail = "no cv2.cuda namespace — a non-CUDA build, which is what JetPack ships"

    return {
        "value": raw,
        "source": src,
        "status": "ok" if raw else "unknown",
        "cuda_devices": cuda_devices,
        "cuda_enabled": bool(cuda_devices),
        "detail": detail,
    }

# Probe 4
def probe_tensorrt(env: Env) -> dict[str, Any]:
    src = "import tensorrt"
    try:
        trt = env.importer("tensorrt")
    except ModuleNotAvailable as e:
        hint = ""
        if env.python.prefix and env.python.prefix != env.python.base_prefix:
            hint = (
                " — you are inside a virtual environment, and TensorRT is a system "
                "package that a venv made without –system-site-packages cannot see"
            )
        return unknown(src, f"tensorrt is not importable: {e}{hint}")

    raw = getattr_path(trt, "__version__")
    if not raw:
        return unknown(src, "tensorrt imported but exposes no __version__")

    return {
        "value": raw,
        "source": src,
        "status": "ok",
        "line": major_minor(str(raw)),
    }

# Probe 5
def probe_l4t(env: Env) -> dict[str, Any]:
    src = "/etc/nv_tegra_release"
    raw = read_text(env.root, src)
    if not raw:
        return unknown(src, "not a Jetson, or the L4T release file is absent")

    release = _L4T_RELEASE.search(raw)
    revision = _L4T_REVISION.search(raw)
    if release is None or revision is None:
        return unknown(
            src,
            f"release file present but unparseable: {raw.splitlines()[0][:80]}",
        )

    version = f"{release.group(1)}.{revision.group(1)}"
    return {
        "value": version,
        "source": src,
        "status": "ok",
        "line": major_minor(version),
        "raw": raw.splitlines()[0],
    }

## for debugging - uncomment the following lines for debugging.
#if __name__ == "__main__":
    #env = Env.real()
    #out = probe_l4t(env)
    #print(out)

# for generating system_report.json
if __name__ == "__main__":
    # calling base environment
    env = Env.real()

    # testing probes
    report = {
        "probe_torch": probe_torch(env),
        "probe_cuda": probe_cuda(env),
        "probe_opencv": probe_opencv(env),
        "probe_tensorrt": probe_tensorrt(env),
        "probe_l4t": probe_l4t(env),
    }
    
    path = "system_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
