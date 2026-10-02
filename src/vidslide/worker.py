"""Worker process wrapper for legacy extraction engine.

Isolates the legacy extractor in a separate process to prevent stdout pollution
and enable proper progress tracking.
"""

import multiprocessing as mp
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from queue import Empty

from vidslide.protocol import EventType


class WorkerMessage:
    """Messages sent from worker to parent."""

    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SLIDE_SAVED = "SLIDE_SAVED"
    DONE = "DONE"
    ERROR = "ERROR"


def _worker_process(
    video_path: str,
    output_dir: str,
    params: Dict[str, Any],
    message_queue: mp.Queue,
    cancel_event: mp.Event,
    log_file: Optional[str] = None,
):
    """Worker process entry point.

    Runs in isolated process. All print() goes to log file.

    Args:
        video_path: Path to video file
        output_dir: Output directory for assets
        params: Extraction parameters
        message_queue: Queue for sending messages to parent
        cancel_event: Event for cancellation signal (sticky)
        log_file: Optional log file for stdout/stderr
    """
    # fd-level redirect for stdout/stderr
    original_stdout_fd = None
    original_stderr_fd = None
    log_fd = None

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

        # Save original fds
        original_stdout_fd = os.dup(sys.stdout.fileno())
        original_stderr_fd = os.dup(sys.stderr.fileno())

        # Redirect at fd level
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())

    try:
        # Signal start
        message_queue.put({"type": WorkerMessage.STARTED})

        # Lazy import to avoid loading cv2 in parent process
        from vidslide.engine.legacy_v041_original import extract_slides

        # Map params to engine signature
        threshold = params.get("threshold", 5.0)
        enable_history = params.get("enable_history", True)
        max_history = params.get("max_history", 5)
        use_roi = params.get("use_roi", True)
        fast_mode = params.get("fast_mode", True)

        # Map decoder to use_gpu
        decoder = params.get("decoder", "auto")
        use_gpu = decoder != "cpu"

        # Validate and whitelist speed_mode
        speed_mode = params.get("speed_mode", "fast")
        if speed_mode not in ("eco", "fast"):
            speed_mode = "fast"

        # Track slides for SLIDE_SAVED detection
        last_saved_count = 0
        last_progress_time = 0
        PROGRESS_THROTTLE = 0.5  # seconds

        def on_progress(saved, pct, message, eta_s, elapsed_s, current_frame):
            """Adapter: engine callback -> message queue."""
            nonlocal last_saved_count, last_progress_time

            import time
            current_time = time.time()

            # Detect new slide
            if saved > last_saved_count:
                # Calculate provenance
                frame_rate = params.get("_fps", 30)  # Passed from probe
                source_time_seconds = current_frame / frame_rate if frame_rate > 0 else 0

                message_queue.put({
                    "type": WorkerMessage.SLIDE_SAVED,
                    "slide_index": saved - 1,  # 0-based
                    "source_frame": current_frame,
                    "source_time_seconds": source_time_seconds,
                })
                last_saved_count = saved

            # Throttle progress updates
            if current_time - last_progress_time >= PROGRESS_THROTTLE:
                message_queue.put({
                    "type": WorkerMessage.PROGRESS,
                    "progress": pct,
                    "message": message,
                    "eta_seconds": eta_s,
                    "elapsed_seconds": elapsed_s,
                    "current_frame": current_frame,
                    "slides_saved": saved,
                })
                last_progress_time = current_time

        def should_cancel():
            """Check sticky cancel event."""
            return cancel_event.is_set()

        # Call legacy engine
        status, message, saved = extract_slides(
            video_path=video_path,
            output_dir=output_dir,
            threshold=threshold,
            enable_history=enable_history,
            max_history=max_history,
            use_roi=use_roi,
            fast_mode=fast_mode,
            use_gpu=use_gpu,
            speed_mode=speed_mode,
            on_progress=on_progress,
            should_cancel=should_cancel,
            start_frame=0,
            saved_offset=0,
        )

        # Map return value to message
        if status == "done":
            message_queue.put({
                "type": WorkerMessage.DONE,
                "slides": saved,
                "message": message,
            })
        elif status == "cancelled":
            message_queue.put({
                "type": WorkerMessage.ERROR,
                "error": "Extraction cancelled by user",
                "error_type": "CancelledError",
            })
        else:  # error
            message_queue.put({
                "type": WorkerMessage.ERROR,
                "error": message,
                "error_type": "ExtractionError",
            })

    except Exception as e:
        import traceback
        message_queue.put({
            "type": WorkerMessage.ERROR,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        })

    finally:
        # Restore fds
        if log_fd is not None:
            os.close(log_fd)
        if original_stdout_fd is not None:
            os.dup2(original_stdout_fd, sys.stdout.fileno())
            os.close(original_stdout_fd)
        if original_stderr_fd is not None:
            os.dup2(original_stderr_fd, sys.stderr.fileno())
            os.close(original_stderr_fd)


class ExtractionWorker:
    """Manages extraction worker process."""

    def __init__(
        self,
        video_path: str,
        output_dir: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize worker.

        Args:
            video_path: Path to video file
            output_dir: Output directory
            params: Extraction parameters
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.params = params or {}

        self.process: Optional[mp.Process] = None
        self.message_queue: Optional[mp.Queue] = None
        self.cancel_event: Optional[mp.Event] = None
        self.log_file: Optional[str] = None

    def start(self, log_file: Optional[str] = None) -> None:
        """Start worker process.

        Args:
            log_file: Optional path for worker logs
        """
        self.log_file = log_file
        self.message_queue = mp.Queue()
        self.cancel_event = mp.Event()

        self.process = mp.Process(
            target=_worker_process,
            args=(
                self.video_path,
                self.output_dir,
                self.params,
                self.message_queue,
                self.cancel_event,
                self.log_file,
            ),
        )
        self.process.start()

    def cancel(self) -> None:
        """Request cancellation (sticky)."""
        if self.cancel_event:
            self.cancel_event.set()

    def get_message(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Get next message from worker.

        Args:
            timeout: Timeout in seconds

        Returns:
            Message dict or None if no message available
        """
        if not self.message_queue:
            return None

        try:
            return self.message_queue.get(timeout=timeout)
        except Empty:
            return None

    def is_alive(self) -> bool:
        """Check if worker is still running."""
        return self.process is not None and self.process.is_alive()

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for worker to complete.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Exit code (0 = success)
        """
        if self.process:
            self.process.join(timeout)
            return self.process.exitcode or 0
        return 0

    def terminate(self) -> None:
        """Terminate worker process."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5.0)

    def kill(self) -> None:
        """Kill worker process (force)."""
        if self.process and self.process.is_alive():
            self.process.kill()
            self.process.join(timeout=1.0)


__all__ = ["ExtractionWorker", "WorkerMessage"]
