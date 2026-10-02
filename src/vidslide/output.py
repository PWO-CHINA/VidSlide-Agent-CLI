"""Output utilities for JSON/JSONL protocol."""

import json
import sys
from typing import Any, Dict, List, Optional

from vidslide.protocol import CommandStatus, ProtocolVersion


def output_json(data: Dict[str, Any]) -> None:
    """Write JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


def output_jsonl(data: Dict[str, Any]) -> None:
    """Write JSONL line to stdout."""
    output_json(data)


def make_result(
    command: str,
    status: CommandStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    next_actions: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a standard result envelope."""
    output = {
        "protocol_version": ProtocolVersion.V1.value,
        "command": command,
        "status": status.value,
    }

    if result:
        output["result"] = result

    if error:
        output["error"] = error

    if warnings:
        output["warnings"] = warnings

    if next_actions:
        output["next_actions"] = next_actions

    # Add any additional fields
    output.update(kwargs)

    return output


def make_progress_event(
    command: str,
    progress: float,
    message: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a progress event for JSONL streaming."""
    event = {
        "protocol_version": ProtocolVersion.V1.value,
        "type": "progress",
        "command": command,
        "progress": progress,
    }

    if message:
        event["message"] = message

    event.update(kwargs)
    return event


def make_error_result(
    command: str,
    error_code: str,
    error_message: str,
    retryable: bool = False,
    next_actions: Optional[List[Dict[str, Any]]] = None,
    **error_details,
) -> Dict[str, Any]:
    """Create an error result."""
    error = {
        "code": error_code,
        "message": error_message,
        "retryable": retryable,
    }
    error.update(error_details)

    return make_result(
        command=command,
        status=CommandStatus.ERROR,
        error=error,
        next_actions=next_actions,
    )


__all__ = [
    "output_json",
    "output_jsonl",
    "make_result",
    "make_progress_event",
    "make_error_result",
]
