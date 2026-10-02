"""Extract command implementation."""

from pathlib import Path
from typing import Optional

from vidslide.probe import probe_video
from vidslide.run import Run
from vidslide.worker import ExtractionWorker, WorkerMessage
from vidslide.protocol import RunState, EventType
from vidslide.output import output_jsonl, make_result, make_progress_event
from vidslide.errors import ExtractionFailedError, WorkerCrashedError


def extract_video(
    video_path: str,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
    resume: bool = False,
) -> dict:
    """Extract slides from video.

    Args:
        video_path: Path to video file
        output_dir: Output directory (default: VIDEO.vidslide)
        overwrite: Overwrite existing output
        resume: Resume incomplete extraction

    Returns:
        Result dictionary

    Raises:
        Various VidSlideError subclasses
    """
    # First probe the video
    video_info = probe_video(video_path)

    # Create or resume run
    if resume and output_dir and Path(output_dir).exists():
        run = Run(Path(output_dir))
        if not run.is_valid():
            raise ExtractionFailedError("Invalid run directory for resume")

        # Check state is resumable
        current_state = run.manifest.data.get("state")
        if current_state == RunState.EXTRACTED.value:
            raise ExtractionFailedError("Run already completed, cannot resume")
        elif current_state == RunState.FAILED.value:
            raise ExtractionFailedError("Run failed, use --overwrite to restart")
        elif current_state != RunState.EXTRACTING.value:
            raise ExtractionFailedError(f"Cannot resume from state: {current_state}")

        # Verify video file matches
        input_sha256 = run.manifest.data.get("input", {}).get("sha256")
        if input_sha256 and input_sha256 != video_info["sha256"]:
            raise ExtractionFailedError(
                "Video file SHA256 mismatch. Original video may have changed. "
                "Use --overwrite to extract from current video."
            )

        # Log resume event
        run.events.append(
            EventType.EXTRACTION_STARTED,
            {
                "run_id": run.manifest.run_id,
                "engine": "legacy-v041",
                "profile": "reliable",
                "resumed": True,
                "existing_slides": len(run.manifest.data.get("assets", {})),
            },
        )

        output_jsonl(
            make_progress_event(
                command="extract",
                progress=0.0,
                message=f"Resuming extraction ({len(run.manifest.data.get('assets', {}))} slides already extracted)",
                run_id=run.manifest.run_id,
            )
        )
    else:
        run = Run.create(
            video_path=video_path,
            video_info=video_info,
            output_dir=output_dir,
            overwrite=overwrite,
        )

    # Update state to EXTRACTING
    run.manifest.update_state(RunState.EXTRACTING)
    run.save_manifest()
    run.events.append(
        EventType.EXTRACTION_STARTED,
        {
            "run_id": run.manifest.run_id,
            "engine": "legacy-v041",
            "profile": "reliable",
        },
    )

    # Output initial progress
    output_jsonl(
        make_progress_event(
            command="extract",
            progress=0.0,
            message="Starting extraction",
            run_id=run.manifest.run_id,
        )
    )

    # Start worker
    log_file = str(run.logs_dir / "legacy-worker.log")

    # Pass fps to worker for provenance calculation
    params_with_fps = run.manifest.data["parameters"].copy()
    params_with_fps["_fps"] = video_info["fps"]

    worker = ExtractionWorker(
        video_path=video_path,
        output_dir=str(run.assets_dir),
        params=params_with_fps,
    )

    try:
        worker.start(log_file=log_file)

        # Process worker messages - drain until terminal message
        slides_extracted = 0
        received_terminal = False

        while True:
            msg = worker.get_message(timeout=0.5)

            if msg:
                msg_type = msg.get("type")

                if msg_type == WorkerMessage.STARTED:
                    pass  # Already sent initial progress

                elif msg_type == WorkerMessage.PROGRESS:
                    output_jsonl(
                        make_progress_event(
                            command="extract",
                            progress=msg.get("progress", 0.0),
                            message=msg.get("message", ""),
                            run_id=run.manifest.run_id,
                            slides=slides_extracted,
                        )
                    )

                elif msg_type == WorkerMessage.SLIDE_SAVED:
                    slides_extracted += 1

                    # Add asset to manifest
                    slide_index = msg.get("slide_index", slides_extracted - 1)
                    source_frame = msg.get("source_frame", 0)
                    source_time = msg.get("source_time_seconds", 0.0)

                    # Legacy engine saves as slide_0000.jpg, slide_0001.jpg, etc.
                    asset_filename = f"slide_{slide_index:04d}.jpg"

                    from vidslide.ids import generate_id
                    asset_id = generate_id("a")

                    run.manifest.add_asset(
                        asset_id=asset_id,
                        asset_path=asset_filename,
                        source_frame=source_frame,
                        source_time_seconds=source_time,
                    )
                    run.save_manifest()

                    run.events.append(
                        EventType.ASSET_CREATED,
                        {
                            "run_id": run.manifest.run_id,
                            "asset_id": asset_id,
                            "filename": asset_filename,
                            "source_frame": source_frame,
                        }
                    )

                elif msg_type == WorkerMessage.ERROR:
                    error_msg = msg.get("error", "Unknown error")
                    received_terminal = True
                    raise ExtractionFailedError(error_msg)

                elif msg_type == WorkerMessage.DONE:
                    slides_extracted = msg.get("slides", slides_extracted)
                    received_terminal = True
                    break

            elif not worker.is_alive():
                # Worker died without sending terminal message
                if not received_terminal:
                    raise WorkerCrashedError("Worker process crashed unexpectedly")
                break

        # Update state to EXTRACTED
        run.manifest.update_state(RunState.EXTRACTED)
        run.save_manifest()
        run.events.append(
            EventType.EXTRACTION_COMPLETED,
            {
                "run_id": run.manifest.run_id,
                "slides": slides_extracted,
            },
        )

        return {
            "run_id": run.manifest.run_id,
            "state": RunState.EXTRACTED.value,
            "slides": slides_extracted,
            "run_dir": str(run.run_dir.absolute()),
        }

    except Exception as e:
        # Clean up worker on error
        if worker.is_alive():
            worker.terminate()

        # Update state to FAILED
        run.manifest.update_state(RunState.FAILED)
        run.save_manifest()
        run.events.append(
            EventType.EXTRACTION_FAILED,
            {
                "run_id": run.manifest.run_id,
                "error": str(e),
            },
        )
        raise


__all__ = ["extract_video"]
