"""Resolve workflow - interactive ambiguity resolution for extracted runs."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from vidslide.protocol import EventType


class ResolveError(Exception):
    """Base exception for resolve errors."""
    pass


class InvalidActionError(ResolveError):
    """Raised when resolve action is invalid."""
    pass


def apply_resolve_action(
    run_dir: str,
    action: Dict[str, Any],
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply a resolve action to a run.

    Args:
        run_dir: Path to run directory
        action: Resolve action specification
        reason: Optional human-readable reason

    Returns:
        Result dictionary with changes applied

    Raises:
        ResolveError: If action cannot be applied
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    events_path = run_dir / "events.jsonl"

    if not manifest_path.exists():
        raise ResolveError(f"No manifest.json found in {run_dir}")

    # Load manifest
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ResolveError(f"Invalid manifest.json: {e}")

    # Validate action structure
    action_type = action.get("type")
    if not action_type:
        raise InvalidActionError("Action must have 'type' field")

    valid_types = ["remove_from_sequence", "insert_into_sequence", "accept_gap", "mark_duplicate"]
    if action_type not in valid_types:
        raise InvalidActionError(f"Invalid action type: {action_type}. Valid: {valid_types}")

    # Apply action based on type
    result = {"action": action_type, "changes": []}

    if action_type == "remove_from_sequence":
        # Remove asset from sequence (doesn't delete the asset itself)
        asset_id = action.get("asset_id")
        if not asset_id:
            raise InvalidActionError("remove_from_sequence requires 'asset_id'")

        sequence = manifest.get("sequence", [])
        if asset_id not in sequence:
            raise ResolveError(f"Asset {asset_id} not in sequence")

        # Remove from sequence
        index = sequence.index(asset_id)
        sequence.remove(asset_id)
        manifest["sequence"] = sequence

        result["changes"].append({
            "field": "sequence",
            "action": "removed",
            "asset_id": asset_id,
            "previous_index": index,
        })

    elif action_type == "insert_into_sequence":
        # Insert asset into sequence at specific position
        asset_id = action.get("asset_id")
        position = action.get("position")

        if not asset_id:
            raise InvalidActionError("insert_into_sequence requires 'asset_id'")
        if position is None:
            raise InvalidActionError("insert_into_sequence requires 'position'")

        assets = manifest.get("assets", {})
        if asset_id not in assets:
            raise ResolveError(f"Asset {asset_id} not found in assets")

        sequence = manifest.get("sequence", [])
        if asset_id in sequence:
            raise ResolveError(f"Asset {asset_id} already in sequence")

        # Insert at position
        sequence.insert(position, asset_id)
        manifest["sequence"] = sequence

        result["changes"].append({
            "field": "sequence",
            "action": "inserted",
            "asset_id": asset_id,
            "position": position,
        })

    elif action_type == "accept_gap":
        # Mark a gap as intentional (add metadata)
        after_asset_id = action.get("after_asset_id")
        if not after_asset_id:
            raise InvalidActionError("accept_gap requires 'after_asset_id'")

        # Add metadata to manifest (for future reference)
        if "resolve_metadata" not in manifest:
            manifest["resolve_metadata"] = {}

        gap_key = f"gap_after_{after_asset_id}"
        manifest["resolve_metadata"][gap_key] = {
            "type": "accepted_gap",
            "reason": reason or "Gap accepted by user",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        result["changes"].append({
            "field": "resolve_metadata",
            "action": "added",
            "key": gap_key,
        })

    elif action_type == "mark_duplicate":
        # Mark asset as duplicate (add metadata, optionally remove from sequence)
        asset_id = action.get("asset_id")
        duplicate_of = action.get("duplicate_of")
        remove = action.get("remove", False)

        if not asset_id:
            raise InvalidActionError("mark_duplicate requires 'asset_id'")
        if not duplicate_of:
            raise InvalidActionError("mark_duplicate requires 'duplicate_of'")

        # Add metadata
        if "resolve_metadata" not in manifest:
            manifest["resolve_metadata"] = {}

        dup_key = f"duplicate_{asset_id}"
        manifest["resolve_metadata"][dup_key] = {
            "type": "duplicate",
            "duplicate_of": duplicate_of,
            "reason": reason or "Marked as duplicate",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        result["changes"].append({
            "field": "resolve_metadata",
            "action": "added",
            "key": dup_key,
        })

        # Optionally remove from sequence
        if remove:
            sequence = manifest.get("sequence", [])
            if asset_id in sequence:
                index = sequence.index(asset_id)
                sequence.remove(asset_id)
                manifest["sequence"] = sequence

                result["changes"].append({
                    "field": "sequence",
                    "action": "removed",
                    "asset_id": asset_id,
                    "previous_index": index,
                })

    # Save updated manifest
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        raise ResolveError(f"Failed to save manifest: {e}")

    # Log resolve event
    resolve_event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "RESOLVE_ACTION_APPLIED",
        "data": {
            "action_type": action_type,
            "reason": reason,
            "changes": result["changes"],
        }
    }

    try:
        with open(events_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(resolve_event) + "\n")
    except Exception:
        # Non-fatal if we can't append to events
        result["warning"] = "Could not append to events.jsonl"

    result["success"] = True
    result["run_dir"] = str(run_dir)

    return result


def cmd_resolve(args) -> int:
    """CLI handler for 'vidslide resolve' command."""
    try:
        # Parse action from JSON string
        if hasattr(args, 'action_json') and args.action_json:
            try:
                action = json.loads(args.action_json)
            except json.JSONDecodeError as e:
                error_result = {
                    "success": False,
                    "error": "invalid_json",
                    "message": f"Invalid JSON in action: {e}"
                }
                print(json.dumps(error_result, indent=2))
                return 1
        else:
            error_result = {
                "success": False,
                "error": "missing_action",
                "message": "No action provided. Use --action-json with JSON action specification."
            }
            print(json.dumps(error_result, indent=2))
            return 1

        result = apply_resolve_action(
            run_dir=args.run_dir,
            action=action,
            reason=getattr(args, 'reason', None)
        )

        print(json.dumps(result, indent=2))
        return 0

    except InvalidActionError as e:
        error_result = {
            "success": False,
            "error": "invalid_action",
            "message": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

    except ResolveError as e:
        error_result = {
            "success": False,
            "error": "resolve_failed",
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


__all__ = ["apply_resolve_action", "cmd_resolve", "ResolveError", "InvalidActionError"]
