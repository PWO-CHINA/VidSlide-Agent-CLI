"""Overview command - generate human-readable summaries of runs."""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def format_size_mb(size_bytes: int) -> float:
    """Format bytes as MB."""
    return round(size_bytes / (1024 * 1024), 1)


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs:.1f}s")

    return " ".join(parts)


def get_run_overview(run_dir: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Generate overview summary of a run.

    Args:
        run_dir: Path to run directory
        verbose: Include additional details

    Returns:
        Overview dictionary with summary information
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    events_path = run_dir / "events.jsonl"

    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json found in {run_dir}")

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Extract basic info
    run_id = manifest.get("run_id")
    state = manifest.get("state")
    engine = manifest.get("engine", "unknown")

    input_info = manifest.get("input", {})
    assets_dict = manifest.get("assets", {})
    sequence = manifest.get("sequence", [])

    # Video information
    video_info = {
        "filename": input_info.get("filename", "unknown"),
        "path": input_info.get("path", ""),
        "duration_seconds": input_info.get("duration_seconds", 0),
        "duration": format_duration(input_info.get("duration_seconds", 0)),
        "resolution": f"{input_info.get('width', 0)}x{input_info.get('height', 0)}",
        "fps": input_info.get("fps", 0),
    }

    if "size_bytes" in input_info:
        video_info["size_mb"] = format_size_mb(input_info["size_bytes"])

    if verbose:
        video_info["sha256"] = input_info.get("sha256", "")[:16] + "..."

    # Extraction information
    extraction_info = {
        "engine": engine,
        "state": state,
        "slide_count": len(sequence),
    }

    # Parse events for timing
    started_at = None
    completed_at = None
    event_count = 0

    if events_path.exists():
        try:
            with open(events_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        event = json.loads(line)
                        event_count += 1

                        if event.get("event") == "EXTRACTION_STARTED" and not started_at:
                            started_at = event.get("timestamp")
                        elif event.get("event") == "EXTRACTION_COMPLETED":
                            completed_at = event.get("timestamp")
        except Exception:
            pass

    if started_at:
        extraction_info["started_at"] = started_at

    if completed_at:
        extraction_info["completed_at"] = completed_at

    if started_at and completed_at:
        try:
            start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            duration_seconds = (end_dt - start_dt).total_seconds()
            extraction_info["duration_seconds"] = duration_seconds
            extraction_info["duration"] = format_duration(duration_seconds)
        except Exception:
            pass

    # Quality indicators
    quality_indicators = {}

    duration_seconds = input_info.get("duration_seconds", 0)
    slide_count = len(sequence)

    if duration_seconds > 0 and slide_count > 0:
        coverage = slide_count / (duration_seconds / 60)  # slides per minute
        quality_indicators["coverage_slides_per_minute"] = round(coverage, 2)

        # Calculate average slide duration
        avg_slide_duration = duration_seconds / slide_count
        quality_indicators["avg_slide_duration_seconds"] = round(avg_slide_duration, 1)
        quality_indicators["avg_slide_duration"] = format_duration(avg_slide_duration)

    # Detect potential issues
    potential_issues = []

    if state == "FAILED":
        potential_issues.append("Extraction failed")
    elif state == "EXTRACTING":
        potential_issues.append("Extraction incomplete")

    if slide_count == 0 and state == "EXTRACTED":
        potential_issues.append("No slides extracted")
    elif slide_count < 5:
        potential_issues.append(f"Very few slides ({slide_count})")

    if quality_indicators.get("coverage_slides_per_minute", 0) > 2:
        potential_issues.append("Very high slide density (>2/min)")
    elif quality_indicators.get("coverage_slides_per_minute", 0) < 0.1:
        potential_issues.append("Very low slide density (<0.1/min)")

    if potential_issues:
        quality_indicators["potential_issues"] = potential_issues

    # Determine next actions
    next_actions = []

    if state == "EXTRACTED":
        next_actions.append(f"vidslide validate {run_dir.name}")
        next_actions.append(f"vidslide export {run_dir.name}")
        next_actions.append(f"vidslide context {run_dir.name}")
    elif state == "EXTRACTING":
        next_actions.append(f"vidslide extract VIDEO --resume --output {run_dir.name}")
    elif state == "FAILED":
        next_actions.append(f"vidslide recover {run_dir.name}")
        next_actions.append(f"vidslide extract VIDEO --overwrite --output {run_dir.name}")

    # Build result
    result = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "video": video_info,
        "extraction": extraction_info,
        "quality_indicators": quality_indicators,
        "next_actions": next_actions,
    }

    if verbose:
        result["event_count"] = event_count
        result["manifest_schema_version"] = manifest.get("schema_version")
        result["protocol_version"] = manifest.get("protocol_version")

    return result


def format_text_overview(overview: Dict[str, Any]) -> str:
    """Format overview as human-readable text."""
    lines = []

    lines.append(f"Run: {overview['run_id']}")
    lines.append(f"Directory: {overview['run_dir']}")
    lines.append("")

    video = overview["video"]
    lines.append("Video:")
    lines.append(f"  File: {video['filename']}")
    lines.append(f"  Duration: {video['duration']}")
    lines.append(f"  Resolution: {video['resolution']} @ {video['fps']} fps")
    if "size_mb" in video:
        lines.append(f"  Size: {video['size_mb']} MB")
    lines.append("")

    extraction = overview["extraction"]
    lines.append("Extraction:")
    lines.append(f"  Engine: {extraction['engine']}")
    lines.append(f"  State: {extraction['state']}")
    lines.append(f"  Slides: {extraction['slide_count']}")
    if "duration" in extraction:
        lines.append(f"  Duration: {extraction['duration']}")
    if "started_at" in extraction:
        lines.append(f"  Started: {extraction['started_at']}")
    if "completed_at" in extraction:
        lines.append(f"  Completed: {extraction['completed_at']}")
    lines.append("")

    quality = overview.get("quality_indicators", {})
    if quality:
        lines.append("Quality:")
        if "coverage_slides_per_minute" in quality:
            lines.append(f"  Coverage: {quality['coverage_slides_per_minute']} slides/min")
        if "avg_slide_duration" in quality:
            lines.append(f"  Avg duration: {quality['avg_slide_duration']}")
        if "potential_issues" in quality:
            lines.append("  Issues:")
            for issue in quality["potential_issues"]:
                lines.append(f"    - {issue}")
        lines.append("")

    next_actions = overview.get("next_actions", [])
    if next_actions:
        lines.append("Next Actions:")
        for action in next_actions:
            lines.append(f"  {action}")

    return "\n".join(lines)


def cmd_overview(args) -> int:
    """CLI handler for 'vidslide overview' command."""
    try:
        overview = get_run_overview(
            run_dir=args.run_dir,
            verbose=getattr(args, 'verbose', False)
        )

        if getattr(args, 'format', 'json') == 'text':
            print(format_text_overview(overview))
        else:
            print(json.dumps(overview, indent=2))

        return 0

    except FileNotFoundError as e:
        error_result = {
            "success": False,
            "error": "run_not_found",
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


__all__ = ["get_run_overview", "format_text_overview", "cmd_overview"]
