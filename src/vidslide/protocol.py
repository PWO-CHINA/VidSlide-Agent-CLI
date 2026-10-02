"""Protocol definitions for VidSlide Agent CLI.

Defines the JSON/JSONL output protocol for agent consumption.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ProtocolVersion(Enum):
    """Protocol version for JSON output."""
    V1 = 1


class CommandStatus(Enum):
    """Command execution status."""
    OK = "ok"
    ERROR = "error"


class RunState(Enum):
    """Run state machine states."""
    NEW = "NEW"
    PROBED = "PROBED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    AUDITING = "AUDITING"
    AUDIT_CLEAN = "AUDIT_CLEAN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    OVERVIEW_READY = "OVERVIEW_READY"
    OVERVIEW_REVIEWED = "OVERVIEW_REVIEWED"
    QA_PASS = "QA_PASS"
    READY_TO_EXPORT = "READY_TO_EXPORT"
    EXPORTING = "EXPORTING"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"
    UNRESOLVED = "UNRESOLVED"


class EventType(Enum):
    """Event types for events.jsonl."""
    RUN_CREATED = "RUN_CREATED"
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    ASSET_CREATED = "ASSET_CREATED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    QA_FLAG_CREATED = "QA_FLAG_CREATED"
    CANDIDATE_CREATED = "CANDIDATE_CREATED"
    SEQUENCE_CHANGED = "SEQUENCE_CHANGED"
    QA_PASSED = "QA_PASSED"
    EXPORT_CREATED = "EXPORT_CREATED"
    FORCE_EXPORT = "FORCE_EXPORT"


__all__ = [
    "ProtocolVersion",
    "CommandStatus",
    "RunState",
    "EventType",
]
