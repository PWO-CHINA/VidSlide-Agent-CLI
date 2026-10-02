"""Error recovery for corrupted or incomplete VidSlide runs."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from vidslide.protocol import RunState


class RecoveryError(Exception):
    """Base exception for recovery errors."""
    pass


class RecoveryReport:
    """Holds recovery analysis and suggested actions."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.issues: List[Dict[str, Any]] = []
        self.recoverable = False
        self.suggested_actions: List[str] = []
        self.salvaged_data: Optional[Dict[str, Any]] = None

    def add_issue(self, severity: str, code: str, message: str, details: Optional[Dict] = None):
        """Add an issue to the report."""
        self.issues.append({
            "severity": severity,
            "code": code,
            "message": message,
            "details": details or {}
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "run_dir": str(self.run_dir),
            "recoverable": self.recoverable,
            "issues": self.issues,
            "suggested_actions": self.suggested_actions,
            "salvaged_data": self.salvaged_data,
        }


def analyze_run(run_dir: str) -> RecoveryReport:
    """
    Analyze a potentially corrupted run directory.

    Args:
        run_dir: Path to run directory

    Returns:
        RecoveryReport with analysis and suggested actions
    """
    run_dir = Path(run_dir)
    report = RecoveryReport(run_dir)

    if not run_dir.exists():
        report.add_issue("error", "RUN_DIR_MISSING", f"Run directory does not exist: {run_dir}")
        report.suggested_actions.append("Cannot recover - directory not found")
        return report

    # Check manifest.json
    manifest_path = run_dir / "manifest.json"
    manifest_data = None
    manifest_corrupted = False

    if not manifest_path.exists():
        report.add_issue("error", "MANIFEST_MISSING", "manifest.json not found")
        manifest_corrupted = True
    else:
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            report.add_issue(
                "error",
                "MANIFEST_CORRUPTED",
                f"manifest.json is corrupted: {e}"
            )
            manifest_corrupted = True
        except Exception as e:
            report.add_issue(
                "error",
                "MANIFEST_READ_ERROR",
                f"Failed to read manifest.json: {e}"
            )
            manifest_corrupted = True

    # Check events.jsonl
    events_path = run_dir / "events.jsonl"
    events_valid = False
    events_count = 0

    if events_path.exists():
        try:
            with open(events_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        json.loads(line)  # Validate JSON
                        events_count += 1
            events_valid = True
        except json.JSONDecodeError as e:
            report.add_issue(
                "warning",
                "EVENTS_CORRUPTED",
                f"events.jsonl has invalid JSON: {e}"
            )
        except Exception as e:
            report.add_issue(
                "warning",
                "EVENTS_READ_ERROR",
                f"Failed to read events.jsonl: {e}"
            )
    else:
        report.add_issue("warning", "EVENTS_MISSING", "events.jsonl not found")

    # Check assets directory
    assets_dir = run_dir / "assets"
    asset_files = []

    if assets_dir.exists() and assets_dir.is_dir():
        asset_files = [f.name for f in assets_dir.iterdir() if f.is_file()]
        if not asset_files:
            report.add_issue("warning", "NO_ASSETS", "No asset files found in assets/")
    else:
        report.add_issue("error", "ASSETS_DIR_MISSING", "assets/ directory not found")

    # Determine recovery strategy
    if manifest_corrupted and events_valid and events_count > 0:
        # Strategy 1: Reconstruct manifest from events
        report.recoverable = True
        report.add_issue(
            "info",
            "CAN_RECONSTRUCT",
            f"Can reconstruct manifest from {events_count} events"
        )
        report.suggested_actions.append(
            "Run: vidslide recover --from-events " + str(run_dir)
        )

    elif manifest_corrupted and asset_files:
        # Strategy 2: Salvage from filesystem
        report.recoverable = True
        report.add_issue(
            "info",
            "CAN_SALVAGE",
            f"Can salvage {len(asset_files)} asset files"
        )
        report.suggested_actions.append(
            "Run: vidslide recover --from-assets " + str(run_dir)
        )
        report.salvaged_data = {
            "asset_count": len(asset_files),
            "asset_files": sorted(asset_files[:10])  # Show first 10
        }

    elif not manifest_corrupted and manifest_data:
        # Manifest exists and is valid
        state = manifest_data.get("state")

        if state == RunState.EXTRACTING.value:
            report.recoverable = True
            report.add_issue(
                "info",
                "INCOMPLETE_EXTRACTION",
                "Extraction was interrupted"
            )
            report.suggested_actions.append(
                "Run: vidslide extract VIDEO --resume --output " + str(run_dir)
            )

        elif state == RunState.FAILED.value:
            report.recoverable = True
            report.add_issue(
                "warning",
                "EXTRACTION_FAILED",
                "Previous extraction failed"
            )
            report.suggested_actions.append(
                "Run: vidslide extract VIDEO --overwrite --output " + str(run_dir)
            )

        else:
            report.add_issue(
                "info",
                "RUN_APPEARS_VALID",
                f"Run appears valid (state: {state})"
            )
            report.suggested_actions.append(
                "Run: vidslide validate " + str(run_dir)
            )

    else:
        # Cannot recover
        report.add_issue(
            "error",
            "UNRECOVERABLE",
            "Run cannot be recovered - both manifest and events are missing/corrupted"
        )
        report.suggested_actions.append(
            "Re-extract from original video with --overwrite"
        )

    return report


def reconstruct_from_events(run_dir: Path) -> Dict[str, Any]:
    """
    Attempt to reconstruct manifest.json from events.jsonl.

    Args:
        run_dir: Path to run directory

    Returns:
        Reconstructed manifest data

    Raises:
        RecoveryError: If reconstruction fails
    """
    events_path = run_dir / "events.jsonl"

    if not events_path.exists():
        raise RecoveryError("events.jsonl not found")

    # Parse all events
    events = []
    try:
        with open(events_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except json.JSONDecodeError as e:
        raise RecoveryError(f"Failed to parse events.jsonl: {e}")

    if not events:
        raise RecoveryError("events.jsonl is empty")

    # Build manifest from events
    # This is a simplified reconstruction - in reality would need more logic
    manifest = {
        "schema_version": 1,
        "protocol_version": 1,
        "state": "FAILED",  # Mark as failed since we're recovering
        "assets": {},
        "sequence": [],
    }

    # Extract basic info from first event
    for event in events:
        event_type = event.get("event")

        if event_type == "EXTRACTION_STARTED":
            manifest["run_id"] = event.get("data", {}).get("run_id")
            manifest["engine"] = event.get("data", {}).get("engine")

        elif event_type == "ASSET_CREATED":
            data = event.get("data", {})
            asset_id = data.get("asset_id")
            if asset_id:
                manifest["assets"][asset_id] = {
                    "path": data.get("filename", ""),
                    "source_frame": data.get("source_frame", 0),
                }
                manifest["sequence"].append(asset_id)

    return manifest


def cmd_recover(args) -> int:
    """CLI handler for 'vidslide recover' command."""
    run_dir = Path(args.run_dir)

    report = analyze_run(str(run_dir))

    # Print structured output
    print(json.dumps(report.to_dict(), indent=2))

    return 0 if report.recoverable else 1


__all__ = ["analyze_run", "reconstruct_from_events", "RecoveryReport", "RecoveryError"]
