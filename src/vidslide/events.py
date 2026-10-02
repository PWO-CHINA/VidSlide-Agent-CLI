"""Event log management for VidSlide runs.

Events are append-only records of all operations performed on a run.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from vidslide.protocol import EventType
from vidslide.ids import generate_id


class EventLog:
    """Manages events.jsonl append-only log."""

    def __init__(self, events_path: Path):
        """Initialize event log.

        Args:
            events_path: Path to events.jsonl file
        """
        self.events_path = events_path

    def append(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Append an event to the log.

        Args:
            event_type: Type of event
            data: Event-specific data

        Returns:
            Event ID
        """
        event_id = generate_id("evt")
        event = {
            "event_id": event_id,
            "type": event_type.value,
            "at": datetime.utcnow().isoformat() + "Z",
        }

        if data:
            event.update(data)

        # Append to file (create if doesn't exist)
        with open(self.events_path, "a", encoding="utf-8") as f:
            json.dump(event, f, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        return event_id

    def read_all(self) -> list[Dict[str, Any]]:
        """Read all events from the log.

        Returns:
            List of event dictionaries
        """
        if not self.events_path.exists():
            return []

        events = []
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        return events

    def count(self) -> int:
        """Count total events in log.

        Returns:
            Number of events
        """
        if not self.events_path.exists():
            return 0

        count = 0
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1

        return count


__all__ = ["EventLog"]
