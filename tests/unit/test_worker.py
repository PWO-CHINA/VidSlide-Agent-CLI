"""Unit tests for worker isolation."""

import tempfile
from pathlib import Path
import time

from vidslide.worker import ExtractionWorker, WorkerMessage


def test_worker_starts_and_stops():
    """Test basic worker lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        worker = ExtractionWorker(
            video_path="/test/video.mp4",
            output_dir=tmpdir,
        )

        log_file = Path(tmpdir) / "worker.log"
        worker.start(log_file=str(log_file))

        assert worker.is_alive()

        # Get started message
        msg = worker.get_message(timeout=1.0)
        assert msg is not None
        assert msg["type"] == WorkerMessage.STARTED

        # Wait for completion
        worker.wait(timeout=5.0)
        assert not worker.is_alive()


def test_worker_progress_messages():
    """Test worker sends progress messages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        worker = ExtractionWorker(
            video_path="/test/video.mp4",
            output_dir=tmpdir,
        )

        worker.start()

        messages = []
        timeout_count = 0
        max_timeout = 50  # 5 seconds total

        while worker.is_alive() and timeout_count < max_timeout:
            msg = worker.get_message(timeout=0.1)
            if msg:
                messages.append(msg)
                timeout_count = 0
            else:
                timeout_count += 1

        # Should have received: STARTED, multiple PROGRESS, DONE
        assert len(messages) >= 3
        assert messages[0]["type"] == WorkerMessage.STARTED
        assert messages[-1]["type"] == WorkerMessage.DONE

        # Check for progress messages
        progress_messages = [m for m in messages if m["type"] == WorkerMessage.PROGRESS]
        assert len(progress_messages) > 0


def test_worker_log_file_created():
    """Test worker creates log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "logs" / "worker.log"

        worker = ExtractionWorker(
            video_path="/test/video.mp4",
            output_dir=tmpdir,
        )

        worker.start(log_file=str(log_file))
        worker.wait(timeout=5.0)

        # Log file should exist
        assert log_file.exists()


def test_worker_termination():
    """Test worker can be terminated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        worker = ExtractionWorker(
            video_path="/test/video.mp4",
            output_dir=tmpdir,
        )

        worker.start()
        time.sleep(0.2)  # Let it start

        assert worker.is_alive()
        worker.terminate()
        time.sleep(0.5)

        assert not worker.is_alive()
