"""Unit tests for error definitions."""

from vidslide.errors import (
    InputNotFoundError,
    ExtractionFailedError,
    UnresolvedQAFlagsError,
    get_exit_code,
)


def test_input_not_found_error():
    """Test InputNotFoundError."""
    error = InputNotFoundError("/path/to/video.mp4")

    assert error.code == "INPUT_NOT_FOUND"
    assert error.retryable is False
    assert "/path/to/video.mp4" in error.message
    assert error.details["path"] == "/path/to/video.mp4"

    # Test to_dict
    error_dict = error.to_dict()
    assert error_dict["code"] == "INPUT_NOT_FOUND"
    assert error_dict["retryable"] is False


def test_extraction_failed_error():
    """Test ExtractionFailedError."""
    error = ExtractionFailedError("Worker crashed")

    assert error.code == "EXTRACTION_FAILED"
    assert error.retryable is True
    assert "Worker crashed" in error.message


def test_unresolved_qa_flags_error():
    """Test UnresolvedQAFlagsError with details."""
    error = UnresolvedQAFlagsError(3)

    assert error.code == "UNRESOLVED_QA_FLAGS"
    assert error.retryable is False
    assert error.details["flag_count"] == 3


def test_get_exit_code():
    """Test exit code mapping."""
    assert get_exit_code("INPUT_NOT_FOUND") == 10
    assert get_exit_code("EXTRACTION_FAILED") == 20
    assert get_exit_code("UNRESOLVED_QA_FLAGS") == 32
    assert get_exit_code("INTERNAL_ERROR") == 50
    assert get_exit_code("UNKNOWN_ERROR") == 1  # Default


def test_error_inheritance():
    """Test that all errors inherit from VidSlideError."""
    from vidslide.errors import VidSlideError

    error = InputNotFoundError("/test")
    assert isinstance(error, VidSlideError)
    assert isinstance(error, Exception)
