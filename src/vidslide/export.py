"""PPTX export functionality for VidSlide CLI."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from pptx import Presentation
    from pptx.util import Inches
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


class ExportError(Exception):
    """Base exception for export errors."""
    pass


class PPTXNotAvailableError(ExportError):
    """Raised when python-pptx is not installed."""
    pass


class InvalidRunError(ExportError):
    """Raised when run directory is invalid or incomplete."""
    pass


def export_to_pptx(
    run_dir: Path,
    output_path: Path,
    title: Optional[str] = None,
    **options
) -> Dict[str, Any]:
    """
    Export a completed VidSlide run to PPTX format.

    Args:
        run_dir: Path to run directory containing manifest.json and assets/
        output_path: Where to save the .pptx file
        title: Optional presentation title (defaults to video filename)
        **options: Additional options:
            - include_metadata: Add source info as speaker notes (default: True)
            - slide_layout: 'blank' or 'title' (default: 'blank')

    Returns:
        Dict with:
            - success: bool
            - output_path: str (absolute path to created file)
            - slide_count: int
            - warnings: List[str] (if any)

    Raises:
        PPTXNotAvailableError: If python-pptx not installed
        InvalidRunError: If run directory is invalid
        ExportError: For other export failures
    """
    if not PPTX_AVAILABLE:
        raise PPTXNotAvailableError(
            "python-pptx is not installed. Install with: pip install python-pptx"
        )

    run_dir = Path(run_dir).resolve()
    output_path = Path(output_path).resolve()

    # Validate run directory
    manifest_path = run_dir / "manifest.json"
    assets_dir = run_dir / "assets"

    if not manifest_path.exists():
        raise InvalidRunError(f"No manifest.json found in {run_dir}")

    if not assets_dir.is_dir():
        raise InvalidRunError(f"No assets/ directory found in {run_dir}")

    # Load manifest
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise InvalidRunError(f"Invalid manifest.json: {e}")

    # Validate manifest structure
    state = manifest.get("state")
    if state != "EXTRACTED":
        raise InvalidRunError(
            f"Run is not in EXTRACTED state (current state: {state}). "
            "Only completed extractions can be exported."
        )

    if "assets" not in manifest:
        raise InvalidRunError("Manifest has no 'assets' field")

    if "sequence" not in manifest:
        raise InvalidRunError("Manifest has no 'sequence' field")

    assets_dict = manifest["assets"]
    sequence = manifest["sequence"]

    if not sequence:
        raise InvalidRunError("No slides to export (sequence is empty)")

    # Extract options
    include_metadata = options.get("include_metadata", True)

    # Determine output path
    if output_path is None:
        # Default: run_dir.pptx (e.g., video.vidslide -> video.pptx)
        if run_dir.suffix == ".vidslide":
            output_path = run_dir.with_suffix(".pptx")
        else:
            output_path = run_dir.parent / f"{run_dir.name}.pptx"
    else:
        output_path = Path(output_path)

    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(10)  # 16:9 aspect ratio
    prs.slide_height = Inches(5.625)

    warnings = []
    slides_added = 0

    # Iterate through sequence to maintain order
    for asset_id in sequence:
        if asset_id not in assets_dict:
            warnings.append(f"Asset {asset_id} in sequence not found in assets")
            continue

        asset_data = assets_dict[asset_id]
        filename = asset_data.get("path")

        if not filename:
            warnings.append(f"Asset {asset_id}: no 'path' field in manifest")
            continue

        image_path = assets_dir / filename

        if not image_path.exists():
            warnings.append(f"Asset {asset_id}: file not found: {filename}")
            continue

        # Add blank slide
        blank_slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(blank_slide_layout)

        # Add image to fill entire slide
        try:
            slide.shapes.add_picture(
                str(image_path),
                left=0,
                top=0,
                width=prs.slide_width,
                height=prs.slide_height
            )
            slides_added += 1
        except Exception as e:
            warnings.append(f"Asset {asset_id}: failed to add image: {e}")
            continue

        # Add metadata as notes if requested
        if include_metadata:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame

            metadata_lines = [
                f"Asset ID: {asset_id}",
                f"Filename: {filename}",
            ]

            if "source_frame" in asset_data:
                metadata_lines.append(f"Source Frame: {asset_data['source_frame']}")

            if "source_time_seconds" in asset_data:
                time_s = asset_data["source_time_seconds"]
                minutes = int(time_s // 60)
                seconds = time_s % 60
                metadata_lines.append(f"Source Time: {minutes}m {seconds:.1f}s")

            text_frame.text = "\n".join(metadata_lines)

    # Save presentation
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))
    except Exception as e:
        raise ExportError(f"Failed to save PPTX: {e}")

    return {
        "success": True,
        "output_path": str(output_path.absolute()),
        "slide_count": slides_added,
        "warnings": warnings
    }


def cmd_export(args) -> int:
    """CLI handler for 'vidslide export' command."""
    run_dir = Path(args.run_dir)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default: run_dir.pptx (e.g., video.vidslide -> video.pptx)
        if run_dir.suffix == ".vidslide":
            output_path = run_dir.with_suffix(".pptx")
        else:
            output_path = run_dir.parent / f"{run_dir.name}.pptx"

    try:
        result = export_to_pptx(
            run_dir=run_dir,
            output_path=output_path,
            include_metadata=not args.no_metadata
        )

        # Print structured output
        print(json.dumps(result, indent=2))

        return 0

    except PPTXNotAvailableError as e:
        error_result = {
            "success": False,
            "error": "pptx_not_available",
            "message": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

    except InvalidRunError as e:
        error_result = {
            "success": False,
            "error": "invalid_run",
            "message": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

    except ExportError as e:
        error_result = {
            "success": False,
            "error": "export_failed",
            "message": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": "unexpected_error",
            "message": f"Unexpected error: {type(e).__name__}: {e}"
        }
        print(json.dumps(error_result, indent=2))
        return 1
