"""Error definitions for VidSlide Agent CLI.

All errors inherit from VidSlideError and include machine-readable error codes.
"""

from typing import Optional


class VidSlideError(Exception):
    """Base exception for all VidSlide errors."""

    def __init__(
        self,
        message: str,
        code: str,
        retryable: bool = False,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            **self.details,
        }


# Input errors (exit code 2, 10-13)
class InvalidArgumentsError(VidSlideError):
    """Invalid command line arguments."""

    def __init__(self, message: str):
        super().__init__(message, "INVALID_ARGUMENTS", retryable=False)


class InputNotFoundError(VidSlideError):
    """Input video file not found."""

    def __init__(self, path: str):
        super().__init__(
            f"Input file not found: {path}",
            "INPUT_NOT_FOUND",
            retryable=False,
            details={"path": path},
        )


class UnsupportedVideoError(VidSlideError):
    """Video format not supported."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            f"Unsupported video: {reason}",
            "UNSUPPORTED_VIDEO",
            retryable=False,
            details={"path": path, "reason": reason},
        )


class VideoDecodeFailedError(VidSlideError):
    """Failed to decode video."""

    def __init__(self, path: str, reason: Optional[str] = None):
        msg = f"Video decode failed: {reason}" if reason else "Video decode failed"
        super().__init__(
            msg, "VIDEO_DECODE_FAILED", retryable=True, details={"path": path}
        )


class ProbeFailedError(VidSlideError):
    """Failed to probe video."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            f"Probe failed: {reason}",
            "PROBE_FAILED",
            retryable=True,
            details={"path": path},
        )


# Extraction errors (exit code 20-23)
class ExtractionFailedError(VidSlideError):
    """Extraction process failed."""

    def __init__(self, reason: str):
        super().__init__(
            f"Extraction failed: {reason}", "EXTRACTION_FAILED", retryable=True
        )


class CancelledError(VidSlideError):
    """Operation was cancelled."""

    def __init__(self):
        super().__init__("Operation cancelled", "CANCELLED", retryable=False)


class WorkerCrashedError(VidSlideError):
    """Worker process crashed."""

    def __init__(self, exit_code: Optional[int] = None):
        msg = f"Worker crashed with exit code {exit_code}" if exit_code else "Worker crashed"
        super().__init__(msg, "WORKER_CRASHED", retryable=True)


class ResumeIncompatibleError(VidSlideError):
    """Cannot resume from incompatible state."""

    def __init__(self, reason: str):
        super().__init__(
            f"Resume incompatible: {reason}", "RESUME_INCOMPATIBLE", retryable=False
        )


# Export and QA errors (exit code 30-36)
class ExportFailedError(VidSlideError):
    """Export failed."""

    def __init__(self, reason: str):
        super().__init__(f"Export failed: {reason}", "EXPORT_FAILED", retryable=True)


class QAExecutionFailedError(VidSlideError):
    """QA execution failed."""

    def __init__(self, reason: str):
        super().__init__(
            f"QA execution failed: {reason}", "QA_EXECUTION_FAILED", retryable=True
        )


class UnresolvedQAFlagsError(VidSlideError):
    """Cannot export with unresolved QA flags."""

    def __init__(self, flag_count: int):
        super().__init__(
            f"Cannot export: {flag_count} unresolved QA flags",
            "UNRESOLVED_QA_FLAGS",
            retryable=False,
            details={"flag_count": flag_count},
        )


class InvalidResolutionActionError(VidSlideError):
    """Invalid resolution action."""

    def __init__(self, reason: str):
        super().__init__(
            f"Invalid resolution action: {reason}",
            "INVALID_RESOLUTION_ACTION",
            retryable=False,
        )


class CandidateNotFoundError(VidSlideError):
    """Candidate not found."""

    def __init__(self, candidate_id: str):
        super().__init__(
            f"Candidate not found: {candidate_id}",
            "CANDIDATE_NOT_FOUND",
            retryable=False,
            details={"candidate_id": candidate_id},
        )


class ManifestConflictError(VidSlideError):
    """Manifest revision conflict."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Manifest conflict: expected revision {expected}, got {actual}",
            "MANIFEST_CONFLICT",
            retryable=False,
            details={"expected_revision": expected, "actual_revision": actual},
        )


class InvalidStateTransitionError(VidSlideError):
    """Invalid state transition."""

    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            f"Invalid state transition: {from_state} -> {to_state}",
            "INVALID_STATE_TRANSITION",
            retryable=False,
            details={"from_state": from_state, "to_state": to_state},
        )


# System errors (exit code 40-41, 50)
class InsufficientDiskSpaceError(VidSlideError):
    """Insufficient disk space."""

    def __init__(self, required_gb: float, available_gb: float):
        super().__init__(
            f"Insufficient disk space: need {required_gb:.1f} GB, have {available_gb:.1f} GB",
            "INSUFFICIENT_DISK_SPACE",
            retryable=False,
            details={"required_gb": required_gb, "available_gb": available_gb},
        )


class OutputExistsError(VidSlideError):
    """Output already exists."""

    def __init__(self, path: str):
        super().__init__(
            f"Output already exists: {path}",
            "OUTPUT_EXISTS",
            retryable=False,
            details={"path": path},
        )


class InternalError(VidSlideError):
    """Internal error."""

    def __init__(self, message: str):
        super().__init__(
            f"Internal error: {message}", "INTERNAL_ERROR", retryable=False
        )


# Error code to exit code mapping
ERROR_EXIT_CODES = {
    "INVALID_ARGUMENTS": 2,
    "INPUT_NOT_FOUND": 10,
    "UNSUPPORTED_VIDEO": 11,
    "VIDEO_DECODE_FAILED": 12,
    "PROBE_FAILED": 13,
    "EXTRACTION_FAILED": 20,
    "CANCELLED": 21,
    "WORKER_CRASHED": 22,
    "RESUME_INCOMPATIBLE": 23,
    "EXPORT_FAILED": 30,
    "QA_EXECUTION_FAILED": 31,
    "UNRESOLVED_QA_FLAGS": 32,
    "INVALID_RESOLUTION_ACTION": 33,
    "CANDIDATE_NOT_FOUND": 34,
    "MANIFEST_CONFLICT": 35,
    "INVALID_STATE_TRANSITION": 36,
    "INSUFFICIENT_DISK_SPACE": 40,
    "OUTPUT_EXISTS": 41,
    "INTERNAL_ERROR": 50,
}


def get_exit_code(error_code: str) -> int:
    """Get exit code for error code."""
    return ERROR_EXIT_CODES.get(error_code, 1)


__all__ = [
    "VidSlideError",
    "InvalidArgumentsError",
    "InputNotFoundError",
    "UnsupportedVideoError",
    "VideoDecodeFailedError",
    "ProbeFailedError",
    "ExtractionFailedError",
    "CancelledError",
    "WorkerCrashedError",
    "ResumeIncompatibleError",
    "ExportFailedError",
    "QAExecutionFailedError",
    "UnresolvedQAFlagsError",
    "InvalidResolutionActionError",
    "CandidateNotFoundError",
    "ManifestConflictError",
    "InvalidStateTransitionError",
    "InsufficientDiskSpaceError",
    "OutputExistsError",
    "InternalError",
    "get_exit_code",
]
