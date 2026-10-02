"""Select the best available inference device without making it mandatory."""

from dataclasses import dataclass
import importlib
import logging
import os
import sys
from typing import Any

import torch


@dataclass(frozen=True)
class ComputeDevice:
    device: Any
    backend: str
    description: str


def _cuda_device():
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        index = torch.cuda.current_device()
        name = torch.cuda.get_device_name(index)
        return ComputeDevice(torch.device(f"cuda:{index}"), "cuda", f"NVIDIA CUDA: {name}")
    return None


def _xpu_device():
    xpu = getattr(torch, "xpu", None)
    if xpu is not None and xpu.is_available() and xpu.device_count() > 0:
        index = xpu.current_device()
        name = xpu.get_device_name(index)
        return ComputeDevice(torch.device(f"xpu:{index}"), "xpu", f"Intel XPU: {name}")
    return None


def _mps_device():
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return ComputeDevice(torch.device("mps"), "mps", "Apple Metal (MPS)")
    return None


def _directml_device():
    if sys.platform != "win32":
        return None
    try:
        torch_directml = importlib.import_module("torch_directml")
        device = torch_directml.device()
        name_getter = getattr(torch_directml, "device_name", None)
        name = name_getter(0) if name_getter else "DirectX 12 GPU"
        return ComputeDevice(device, "directml", f"DirectML: {name}")
    except (ImportError, OSError, RuntimeError, TypeError):
        return None


def select_compute_device():
    """Choose an accelerator, with CPU as the always-available fallback."""
    requested = os.environ.get("FACEBLUR_DEVICE", "auto").strip().lower()
    selectors = {
        "cuda": _cuda_device,
        "xpu": _xpu_device,
        "mps": _mps_device,
        "directml": _directml_device,
    }

    if requested == "cpu":
        return ComputeDevice(torch.device("cpu"), "cpu", "CPU")
    if requested != "auto":
        selector = selectors.get(requested)
        selected = selector() if selector else None
        if selected is not None:
            return selected
        logging.warning("Requested compute backend '%s' is unavailable; using CPU", requested)
        return ComputeDevice(torch.device("cpu"), "cpu", "CPU")

    for selector in (_cuda_device, _xpu_device, _mps_device, _directml_device):
        try:
            selected = selector()
        except (OSError, RuntimeError):
            logging.exception("Compute backend probe failed: %s", selector.__name__)
            continue
        if selected is not None:
            return selected
    return ComputeDevice(torch.device("cpu"), "cpu", "CPU")
