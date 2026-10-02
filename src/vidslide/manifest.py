"""Manifest management for VidSlide runs.

The manifest represents the current state snapshot of an extraction run.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from vidslide.protocol import RunState
from vidslide.ids import generate_id


class Manifest:
    """Represents a run's manifest.json state."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize from manifest dict."""
        self.data = data

    @property
    def run_id(self) -> str:
        """Get run ID."""
        return self.data["run_id"]

    @property
    def state(self) -> str:
        """Get current state."""
        return self.data["state"]

    @property
    def revision(self) -> int:
        """Get manifest revision."""
        return self.data.get("revision", 0)

    @property
    def sequence(self) -> List[str]:
        """Get current slide sequence."""
        return self.data.get("sequence", [])

    @property
    def assets(self) -> Dict[str, Any]:
        """Get assets dictionary."""
        return self.data.get("assets", {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data.copy()

    @staticmethod
    def create_new(
        run_id: str,
        video_path: str,
        video_info: Dict[str, Any],
        engine_id: str = "legacy-v041",
        profile: str = "reliable",
    ) -> "Manifest":
        """Create a new manifest for a run.

        Args:
            run_id: Run identifier
            video_path: Path to video file
            video_info: Video metadata from probe
            engine_id: Extraction engine ID
            profile: Engine profile

        Returns:
            New Manifest instance
        """
        now = datetime.utcnow().isoformat() + "Z"

        data = {
            "schema_version": 1,
            "protocol_version": 1,
            "run_id": run_id,
            "created_at": now,
            "updated_at": now,
            "revision": 0,
            "engine": {
                "id": engine_id,
                "source_commit": "66ec86808443509df86fbc8d82e5188d8eb90ffc",
                "profile": profile,
            },
            "input": {
                "path": video_path,
                "sha256": video_info.get("sha256", ""),
                "size_bytes": video_info.get("size_bytes", 0),
            },
            "parameters": {
                "threshold": 5.0,
                "enable_history": True,
                "max_history": 5,
                "use_roi": True,
                "fast_mode": True,
                "speed_mode": "fast",
                "decoder": "auto",
            },
            "video": video_info.get("video", {}),
            "assets": {},
            "sequence": [],
            "qa": {
                "status": "PENDING",
                "audit_revision": 0,
                "open_flags": [],
            },
            "state": RunState.NEW.value,
        }

        return Manifest(data)

    @staticmethod
    def load(manifest_path: Path) -> "Manifest":
        """Load manifest from file.

        Args:
            manifest_path: Path to manifest.json

        Returns:
            Manifest instance
        """
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Manifest(data)

    def save(self, manifest_path: Path, atomic: bool = True) -> None:
        """Save manifest to file.

        Args:
            manifest_path: Path to manifest.json
            atomic: Use atomic write (write to .tmp, then rename)
        """
        self.data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        if atomic:
            tmp_path = manifest_path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            tmp_path.replace(manifest_path)
        else:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

    def update_state(self, new_state: RunState) -> None:
        """Update run state."""
        self.data["state"] = new_state.value
        self.data["revision"] += 1

    def add_asset(
        self,
        asset_id: str,
        asset_path: str,
        source_frame: int,
        source_time_seconds: float,
        sha256: str = "",
    ) -> None:
        """Add an asset to the manifest.

        Args:
            asset_id: Asset identifier (e.g., "s_01K...")
            asset_path: Relative path to asset file
            source_frame: Frame number in source video
            source_time_seconds: Estimated timestamp
            sha256: File hash (optional)
        """
        self.data["assets"][asset_id] = {
            "path": asset_path,
            "sha256": sha256,
            "source_frame": source_frame,
            "source_time_seconds": round(source_time_seconds, 2),
            "time_basis": "fps_derived",
            "timestamp_accuracy": "estimated",
            "origin": self.data["engine"]["id"],
        }

        # Add to sequence
        self.data["sequence"].append(asset_id)
        self.data["revision"] += 1


__all__ = ["Manifest"]
