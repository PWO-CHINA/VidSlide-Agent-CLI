"""Unit tests for CLI protocol output."""

import json
from vidslide.protocol import CommandStatus, ProtocolVersion
from vidslide.output import make_result, make_error_result, make_progress_event


def test_make_result_basic():
    """Test basic result envelope."""
    result = make_result(
        command="test",
        status=CommandStatus.OK,
        result={"data": "value"},
    )

    assert result["protocol_version"] == ProtocolVersion.V1.value
    assert result["command"] == "test"
    assert result["status"] == "ok"
    assert result["result"] == {"data": "value"}


def test_make_result_with_next_actions():
    """Test result with next_actions."""
    result = make_result(
        command="probe",
        status=CommandStatus.OK,
        next_actions=[{"command": "extract", "args": ["video.mp4"]}],
    )

    assert "next_actions" in result
    assert len(result["next_actions"]) == 1
    assert result["next_actions"][0]["command"] == "extract"


def test_make_error_result():
    """Test error result envelope."""
    result = make_error_result(
        command="test",
        error_code="TEST_ERROR",
        error_message="Test error message",
        retryable=True,
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "TEST_ERROR"
    assert result["error"]["message"] == "Test error message"
    assert result["error"]["retryable"] is True


def test_make_progress_event():
    """Test progress event."""
    event = make_progress_event(
        command="extract",
        progress=42.5,
        message="Processing...",
    )

    assert event["type"] == "progress"
    assert event["command"] == "extract"
    assert event["progress"] == 42.5
    assert event["message"] == "Processing..."


def test_json_serialization():
    """Test that output is JSON serializable."""
    result = make_result(
        command="capabilities",
        status=CommandStatus.OK,
        result={"commands": ["probe", "extract"]},
    )

    # Should not raise
    json_str = json.dumps(result)
    assert json_str is not None

    # Should be parseable
    parsed = json.loads(json_str)
    assert parsed["command"] == "capabilities"
