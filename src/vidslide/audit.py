"""Audit command - detailed provenance and decision history."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_audit_trail(
    run_dir: str,
    event_type: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed audit trail from events.jsonl.

    Args:
        run_dir: Path to run directory
        event_type: Optional filter by event type
        asset_id: Optional filter by asset ID

    Returns:
        Audit trail with events and summary
    """
    run_dir = Path(run_dir)
    events_path = run_dir / "events.jsonl"
    manifest_path = run_dir / "manifest.json"

    if not events_path.exists():
        raise FileNotFoundError(f"No events.jsonl found in {run_dir}")

    # Load manifest for context
    manifest_data = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
        except Exception:
            pass

    # Parse events
    events = []
    event_type_counts = {}
    parse_errors = []

    try:
        with open(events_path, 'r', encoding='utf-8') as f:
            line_num = 0
            for line in f:
                line_num += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)

                    # Apply filters
                    evt_type = event.get("event")
                    if event_type and evt_type != event_type:
                        continue

                    if asset_id:
                        evt_data = event.get("data", {})
                        if evt_data.get("asset_id") != asset_id:
                            continue

                    events.append(event)

                    # Count by type
                    event_type_counts[evt_type] = event_type_counts.get(evt_type, 0) + 1

                except json.JSONDecodeError as e:
                    parse_errors.append({
                        "line": line_num,
                        "error": str(e)
                    })

    except Exception as e:
        raise Exception(f"Failed to read events.jsonl: {e}")

    # Build summary
    summary = {
        "total_events": len(events),
        "event_types": event_type_counts,
    }

    if parse_errors:
        summary["parse_errors"] = parse_errors

    # Extract timeline
    timeline = []
    for event in events:
        timeline_entry = {
            "timestamp": event.get("timestamp"),
            "event": event.get("event"),
        }

        # Include relevant data fields
        data = event.get("data", {})
        if data:
            # Filter out verbose fields, keep important ones
            important_fields = [
                "asset_id", "filename", "source_frame", "source_time_seconds",
                "run_id", "engine", "profile", "error", "message", "state"
            ]
            filtered_data = {k: v for k, v in data.items() if k in important_fields}
            if filtered_data:
                timeline_entry["data"] = filtered_data

        timeline.append(timeline_entry)

    # Build result
    result = {
        "run_id": manifest_data.get("run_id"),
        "run_dir": str(run_dir),
        "summary": summary,
        "audit_trail": timeline,
    }

    # Add filters applied
    filters_applied = []
    if event_type:
        filters_applied.append(f"event_type={event_type}")
    if asset_id:
        filters_applied.append(f"asset_id={asset_id}")

    if filters_applied:
        result["filters"] = filters_applied

    return result


def format_text_audit(audit: Dict[str, Any]) -> str:
    """Format audit trail as human-readable text."""
    lines = []

    lines.append(f"Run: {audit.get('run_id', 'unknown')}")
    lines.append(f"Directory: {audit['run_dir']}")
    lines.append("")

    summary = audit["summary"]
    lines.append("Summary:")
    lines.append(f"  Total events: {summary['total_events']}")

    if summary.get("event_types"):
        lines.append("  Event types:")
        for evt_type, count in sorted(summary["event_types"].items()):
            lines.append(f"    {evt_type}: {count}")

    if summary.get("parse_errors"):
        lines.append(f"  Parse errors: {len(summary['parse_errors'])}")

    lines.append("")

    if audit.get("filters"):
        lines.append(f"Filters: {', '.join(audit['filters'])}")
        lines.append("")

    lines.append("Audit Trail:")
    for entry in audit["audit_trail"][:50]:  # Show first 50
        timestamp = entry.get("timestamp", "unknown")
        event = entry.get("event", "unknown")
        lines.append(f"  [{timestamp}] {event}")

        if "data" in entry:
            for key, value in entry["data"].items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                lines.append(f"    {key}: {value_str}")

    if len(audit["audit_trail"]) > 50:
        lines.append(f"  ... and {len(audit['audit_trail']) - 50} more events")

    return "\n".join(lines)


def get_asset_history(run_dir: str, asset_id: str) -> Dict[str, Any]:
    """
    Get complete history for a specific asset.

    Args:
        run_dir: Path to run directory
        asset_id: Asset ID to trace

    Returns:
        Asset history with all related events
    """
    audit = get_audit_trail(run_dir, asset_id=asset_id)

    # Find asset in manifest
    manifest_path = Path(run_dir) / "manifest.json"
    asset_data = None

    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                assets = manifest.get("assets", {})
                asset_data = assets.get(asset_id)
        except Exception:
            pass

    result = {
        "asset_id": asset_id,
        "run_dir": str(run_dir),
        "current_state": asset_data,
        "history": audit["audit_trail"],
        "event_count": audit["summary"]["total_events"],
    }

    return result


def cmd_audit(args) -> int:
    """CLI handler for 'vidslide audit' command."""
    try:
        if hasattr(args, 'asset_id') and args.asset_id:
            # Asset-specific history
            result = get_asset_history(
                run_dir=args.run_dir,
                asset_id=args.asset_id
            )
        else:
            # Full audit trail
            result = get_audit_trail(
                run_dir=args.run_dir,
                event_type=getattr(args, 'event_type', None),
            )

        if getattr(args, 'format', 'json') == 'text':
            print(format_text_audit(result))
        else:
            print(json.dumps(result, indent=2))

        return 0

    except FileNotFoundError as e:
        error_result = {
            "success": False,
            "error": "events_not_found",
            "message": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": "unexpected_error",
            "message": f"{type(e).__name__}: {e}"
        }
        print(json.dumps(error_result, indent=2))
        return 1


__all__ = ["get_audit_trail", "get_asset_history", "format_text_audit", "cmd_audit"]
