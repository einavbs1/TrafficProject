from __future__ import annotations

import logging

import torch

logger = logging.getLogger(__name__)

VALID_DEVICE_PREFERENCES = frozenset({"auto", "cpu", "cuda", "directml"})


def _normalize_preference(preference: str | None) -> str:
    pref = (preference or "auto").strip().lower()
    if pref not in VALID_DEVICE_PREFERENCES:
        return "auto"
    return pref


def directml_available() -> bool:
    try:
        import torch_directml

        _ = torch_directml.device()
        return True
    except Exception:
        return False


def _directml_device() -> torch.device:
    import torch_directml

    return torch_directml.device()


def resolve_training_device(preference: str = "auto") -> tuple[torch.device, str]:
    pref = _normalize_preference(preference)

    if pref == "cpu":
        return torch.device("cpu"), "cpu"

    if pref == "cuda":
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return torch.device("cuda"), f"cuda ({name})"
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False")

    if pref == "directml":
        if directml_available():
            return _directml_device(), "directml"
        raise RuntimeError("DirectML requested but torch-directml is not installed or failed to initialize")

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return torch.device("cuda"), f"cuda ({name})"

    if directml_available():
        return _directml_device(), "directml"

    return torch.device("cpu"), "cpu"


def resolve_training_device_or_fallback(preference: str = "auto") -> tuple[torch.device, str]:
    pref = _normalize_preference(preference)
    try:
        return resolve_training_device(pref)
    except RuntimeError as exc:
        logger.warning("%s; using CPU", exc)
        return torch.device("cpu"), f"cpu (fallback after {pref}: {exc})"


def device_label(device: torch.device) -> str:
    if device.type == "cuda":
        try:
            index = int(device.index or 0)
            return f"cuda:{index} ({torch.cuda.get_device_name(index)})"
        except Exception:
            return str(device)
    return str(device)
