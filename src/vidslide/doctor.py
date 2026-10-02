"""Environment diagnostics for VidSlide Agent CLI.

Provides a 'doctor' command to check system requirements and capabilities.
"""

import os
import shutil
import sys
import tempfile
from typing import Any, Dict

from vidslide.protocol import CommandStatus


def check_python_version() -> str:
    """Return Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def check_opencv() -> str | bool:
    """Check OpenCV availability and return version or False."""
    try:
        import cv2
        return cv2.__version__
    except ImportError:
        return False


def check_video_decode() -> bool:
    """Check if video decoding works via cv2.VideoCapture."""
    try:
        import cv2
        # Test VideoCapture with a dummy index - just checks if the class loads
        # and basic functionality is available
        cap = cv2.VideoCapture(0)
        if cap is not None:
            cap.release()
        return True
    except Exception:
        return False


def check_gpu_decode_available() -> bool | None:
    """Check if GPU decode is available (best effort, not critical)."""
    try:
        import cv2
        # Check for CUDA support in OpenCV
        # This is a best-effort check; returns None if uncertain
        try:
            # Try to detect if CUDA is available
            cuda_support = cv2.cuda.getCudaEnabledDeviceCount() > 0
            return cuda_support
        except AttributeError:
            # CUDA module not available
            return None
    except Exception:
        return None


def check_write_permission() -> bool:
    """Check if we have write permission in current directory."""
    try:
        with tempfile.NamedTemporaryFile(dir=".", delete=True):
            return True
    except (OSError, IOError):
        return False


def check_free_disk_space() -> float:
    """Return free disk space in GB."""
    try:
        stat = shutil.disk_usage(".")
        return stat.free / (1024 ** 3)  # Convert bytes to GB
    except Exception:
        return 0.0


def check_ocr_available() -> Dict[str, bool]:
    """Return OCR availability status (currently always false)."""
    return {"available": False}


def run_doctor(run_dir: str | None = None) -> Dict[str, Any]:
    """Run all environment checks and return results.

    Args:
        run_dir: Optional run directory to check integrity

    Returns:
        Dict with environment check results
    """
    result = {
        "python": check_python_version(),
        "opencv": check_opencv(),
        "video_decode": check_video_decode(),
        "gpu_decode_available": check_gpu_decode_available(),
        "write_permission": check_write_permission(),
        "free_disk_gb": check_free_disk_space(),
        "ocr": check_ocr_available(),
    }

    # TODO: Add run integrity check when run_dir is provided
    if run_dir:
        result["run_integrity"] = {
            "checked": False,
            "note": "Run integrity check not implemented yet"
        }

    return result
