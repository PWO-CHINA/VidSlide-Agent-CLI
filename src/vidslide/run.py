"""Run directory management for VidSlide extractions.

Manages the creation and structure of run directories.
"""

import os
from pathlib import Path
from typing import Optional

from vidslide.ids import generate_id
from vidslide.manifest import Manifest
from vidslide.events import EventLog
from vidslide.protocol import EventType, RunState
from vidslide.errors import OutputExistsError


class Run:
    """Represents a VidSlide extraction run directory."""

    def __init__(self, run_dir: Path):
        """Initialize run from directory.

        Args:
            run_dir: Path to run directory (e.g., video.vidslide/)
        """
        self.run_dir = run_dir
        self.manifest_path = run_dir / "manifest.json"
        self.events_path = run_dir / "events.jsonl"
        self.assets_dir = run_dir / "assets"
        self.candidates_dir = run_dir / "candidates"
        self.review_dir = run_dir / "review"
        self.qa_dir = run_dir / "qa"
        self.logs_dir = run_dir / "logs"
        self.exports_dir = run_dir / "exports"

        self._manifest: Optional[Manifest] = None
        self._events: Optional[EventLog] = None

    @property
    def manifest(self) -> Manifest:
        """Get manifest (lazy load)."""
        if self._manifest is None:
            self._manifest = Manifest.load(self.manifest_path)
        return self._manifest

    @property
    def events(self) -> EventLog:
        """Get event log (lazy load)."""
        if self._events is None:
            self._events = EventLog(self.events_path)
        return self._events

    @staticmethod
    def create(
        video_path: str,
        video_info: dict,
        output_dir: Optional[str] = None,
        overwrite: bool = False,
    ) -> "Run":
        """Create a new run directory.

        Args:
            video_path: Path to video file
            video_info: Video metadata from probe
            output_dir: Output directory (default: VIDEO.vidslide)
            overwrite: Overwrite if exists

        Returns:
            New Run instance

        Raises:
            OutputExistsError: If output exists and overwrite=False
        """
        # Determine output directory
        if output_dir is None:
            video_path_obj = Path(video_path)
            output_dir = str(video_path_obj.with_suffix(".vidslide"))

        run_dir = Path(output_dir)

        # Check if exists
        if run_dir.exists() and not overwrite:
            raise OutputExistsError(str(run_dir))

        # Create directory structure
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "assets").mkdir(exist_ok=True)
        (run_dir / "candidates").mkdir(exist_ok=True)
        (run_dir / "review" / "overview").mkdir(parents=True, exist_ok=True)
        (run_dir / "review" / "context").mkdir(parents=True, exist_ok=True)
        (run_dir / "qa").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "exports").mkdir(exist_ok=True)

        # Generate run ID
        run_id = generate_id("run")

        # Create manifest
        manifest = Manifest.create_new(
            run_id=run_id,
            video_path=video_path,
            video_info=video_info,
        )

        # Save manifest
        manifest.save(run_dir / "manifest.json", atomic=True)

        # Create event log and log creation
        events = EventLog(run_dir / "events.jsonl")
        events.append(
            EventType.RUN_CREATED,
            {
                "run_id": run_id,
                "video_path": video_path,
                "output_dir": str(run_dir.absolute()),
            },
        )

        # Create run instance
        run = Run(run_dir)
        run._manifest = manifest
        run._events = events

        return run

    def save_manifest(self) -> None:
        """Save manifest to disk."""
        if self._manifest:
            self._manifest.save(self.manifest_path, atomic=True)

    def exists(self) -> bool:
        """Check if run directory exists."""
        return self.run_dir.exists()

    def is_valid(self) -> bool:
        """Check if run directory is valid (has manifest and events)."""
        return self.manifest_path.exists() and self.events_path.exists()


__all__ = ["Run"]
