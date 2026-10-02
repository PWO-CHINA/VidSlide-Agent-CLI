"""Video probing utilities for VidSlide Agent CLI.

Provides video metadata extraction and basic decode smoke test.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional

from vidslide.errors import InputNotFoundError, ProbeFailedError


def probe_video(video_path: str) -> Dict[str, Any]:
    """Probe video file and return metadata.

    Args:
        video_path: Path to video file

    Returns:
        Dict with video metadata

    Raises:
        InputNotFoundError: Video file not found
        ProbeFailedError: Failed to probe video
    """
    # Check file exists
    path = Path(video_path)
    if not path.exists():
        raise InputNotFoundError(str(path.absolute()))

    if not path.is_file():
        raise ProbeFailedError(str(path.absolute()), "Path is not a file")

    # Get file info
    try:
        file_size = path.stat().st_size
        file_hash = _compute_sha256(path)
    except Exception as e:
        raise ProbeFailedError(str(path.absolute()), f"Failed to read file: {e}")

    # Try to open with OpenCV
    try:
        import cv2
    except ImportError:
        raise ProbeFailedError(str(path.absolute()), "OpenCV not available")

    cap = cv2.VideoCapture(str(path.absolute()))
    if not cap.isOpened():
        raise ProbeFailedError(str(path.absolute()), "Cannot open video file")

    try:
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

        # Calculate duration
        duration_seconds = frame_count / fps if fps > 0 else 0

        # Try to decode first frame (smoke test)
        ret, frame = cap.read()
        if not ret:
            raise ProbeFailedError(str(path.absolute()), "Cannot decode first frame")

        # Get codec name
        codec = _fourcc_to_string(fourcc) if fourcc else "unknown"

        # Pre-flight validation (parity with GUI)
        if fps <= 0:
            raise ProbeFailedError(str(path.absolute()), "Invalid FPS: must be > 0")
        if frame_count < 10:
            raise ProbeFailedError(str(path.absolute()), "Video too short: must have at least 10 frames")

        result = {
            "path": str(path.absolute()),
            "size_bytes": file_size,
            "sha256": file_hash,
            "video": {
                "duration_seconds": round(duration_seconds, 2),
                "fps_reported": round(fps, 2),
                "width": width,
                "height": height,
                "frame_count_reported": frame_count,
                "codec": codec,
            },
            "recommended_engine": "legacy-v041",
            # Add fps for worker provenance calculation
            "fps": round(fps, 2),
        }

        return result

    finally:
        cap.release()


def _compute_sha256(path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def _fourcc_to_string(fourcc: int) -> str:
    """Convert fourcc code to string."""
    try:
        return "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
    except:
        return "unknown"


__all__ = ["probe_video"]
