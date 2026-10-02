"""Context command - provide semantic context about extracted slides."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timedelta


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration (e.g., '1h 23m 45.2s')."""
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


def get_slide_context(
    run_dir: str,
    slide_index: Optional[int] = None,
    format_type: str = "json"
) -> Dict[str, Any]:
    """
    Get semantic context about slides in a run.

    Args:
        run_dir: Path to run directory
        slide_index: Optional specific slide index (0-based)
        format_type: 'json' or 'text'

    Returns:
        Context dictionary with temporal and spatial information
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json found in {run_dir}")

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Extract basic info
    run_id = manifest.get("run_id")
    state = manifest.get("state")
    assets_dict = manifest.get("assets", {})
    sequence = manifest.get("sequence", [])

    input_info = manifest.get("input", {})
    video_filename = input_info.get("filename", "unknown")
    duration_seconds = input_info.get("duration_seconds", 0)
    fps = input_info.get("fps", 30.0)

    slide_count = len(sequence)

    # Build slide details
    slides = []
    prev_time = None

    for idx, asset_id in enumerate(sequence):
        if asset_id not in assets_dict:
            continue

        asset_data = assets_dict[asset_id]
        source_frame = asset_data.get("source_frame", 0)
        source_time_seconds = asset_data.get("source_time_seconds", source_frame / fps)

        time_since_previous = None
        if prev_time is not None:
            time_since_previous = source_time_seconds - prev_time

        slide_info = {
            "index": idx,
            "asset_id": asset_id,
            "source_frame": source_frame,
            "source_time_seconds": source_time_seconds,
            "source_time": format_duration(source_time_seconds),
            "time_since_previous_seconds": time_since_previous,
            "time_since_previous": format_duration(time_since_previous) if time_since_previous else None,
            "filename": asset_data.get("path", ""),
        }

        # Flag potential issues
        flags = []
        if time_since_previous is not None:
            if time_since_previous < 10:
                flags.append("very_close")
            elif time_since_previous > 600:  # 10 minutes
                flags.append("large_gap")

        if flags:
            slide_info["flags"] = flags

        slides.append(slide_info)
        prev_time = source_time_seconds

    # Calculate statistics
    time_gaps = [s["time_since_previous_seconds"] for s in slides if s["time_since_previous_seconds"]]

    statistics = {
        "slide_count": slide_count,
        "video_duration_seconds": duration_seconds,
        "coverage_percentage": (slide_count / (duration_seconds / 60)) if duration_seconds > 0 else 0,
    }

    if time_gaps:
        statistics.update({
            "avg_time_between_slides_seconds": sum(time_gaps) / len(time_gaps),
            "min_time_between_slides_seconds": min(time_gaps),
            "max_time_between_slides_seconds": max(time_gaps),
            "avg_time_between_slides": format_duration(sum(time_gaps) / len(time_gaps)),
            "min_time_between_slides": format_duration(min(time_gaps)),
            "max_time_between_slides": format_duration(max(time_gaps)),
        })

    # Build result
    result = {
        "run_id": run_id,
        "state": state,
        "video_filename": video_filename,
        "video_duration_seconds": duration_seconds,
        "video_duration": format_duration(duration_seconds),
        "fps": fps,
        "slide_count": slide_count,
        "statistics": statistics,
    }

    # Filter to specific slide if requested
    if slide_index is not None:
        if 0 <= slide_index < len(slides):
            result["slide"] = slides[slide_index]
            # Include neighboring slides for context
            result["context"] = {
                "previous": slides[slide_index - 1] if slide_index > 0 else None,
                "next": slides[slide_index + 1] if slide_index < len(slides) - 1 else None,
            }
        else:
            result["error"] = f"Slide index {slide_index} out of range (0-{len(slides)-1})"
    else:
        result["slides"] = slides

    # Identify potential issues
    issues = []
    very_close_count = sum(1 for s in slides if "flags" in s and "very_close" in s["flags"])
    large_gap_count = sum(1 for s in slides if "flags" in s and "large_gap" in s["flags"])

    if very_close_count > 0:
        issues.append({
            "type": "very_close_slides",
            "count": very_close_count,
            "description": f"{very_close_count} slide(s) within 10 seconds of previous",
            "severity": "warning"
        })

    if large_gap_count > 0:
        issues.append({
            "type": "large_gaps",
            "count": large_gap_count,
            "description": f"{large_gap_count} gap(s) exceeding 10 minutes",
            "severity": "info"
        })

    if issues:
        result["potential_issues"] = issues

    return result


def format_text_output(context: Dict[str, Any]) -> str:
    """Format context as human-readable text."""
    lines = []

    lines.append(f"Run: {context['run_id']}")
    lines.append(f"State: {context['state']}")
    lines.append(f"Video: {context['video_filename']}")
    lines.append(f"Duration: {context['video_duration']} ({context['fps']} fps)")
    lines.append(f"Slides: {context['slide_count']}")
    lines.append("")

    stats = context.get("statistics", {})
    lines.append("Statistics:")
    if "avg_time_between_slides" in stats:
        lines.append(f"  Average gap: {stats['avg_time_between_slides']}")
        lines.append(f"  Min gap: {stats['min_time_between_slides']}")
        lines.append(f"  Max gap: {stats['max_time_between_slides']}")
    lines.append(f"  Coverage: {stats.get('coverage_percentage', 0):.1f} slides/minute")
    lines.append("")

    if "potential_issues" in context:
        lines.append("Potential Issues:")
        for issue in context["potential_issues"]:
            lines.append(f"  - {issue['description']} ({issue['severity']})")
        lines.append("")

    if "slide" in context:
        slide = context["slide"]
        lines.append(f"Slide {slide['index']}:")
        lines.append(f"  Time: {slide['source_time']}")
        lines.append(f"  Frame: {slide['source_frame']}")
        lines.append(f"  File: {slide['filename']}")
        if slide.get("time_since_previous"):
            lines.append(f"  Gap: {slide['time_since_previous']}")
    elif "slides" in context:
        lines.append("Slides:")
        for slide in context["slides"][:10]:  # Show first 10
            gap_str = f" (gap: {slide['time_since_previous']})" if slide.get("time_since_previous") else ""
            flags_str = f" [{', '.join(slide['flags'])}]" if slide.get("flags") else ""
            lines.append(f"  {slide['index']:3d}. {slide['source_time']:>12s}{gap_str}{flags_str}")

        if len(context["slides"]) > 10:
            lines.append(f"  ... and {len(context['slides']) - 10} more")

    return "\n".join(lines)


def cmd_context(args) -> int:
    """CLI handler for 'vidslide context' command."""
    try:
        context = get_slide_context(
            run_dir=args.run_dir,
            slide_index=args.slide if hasattr(args, 'slide') and args.slide is not None else None,
            format_type=getattr(args, 'format', 'json')
        )

        if getattr(args, 'format', 'json') == 'text':
            print(format_text_output(context))
        else:
            print(json.dumps(context, indent=2))

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


__all__ = ["get_slide_context", "format_text_output", "cmd_context"]
