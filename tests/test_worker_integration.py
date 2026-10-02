"""Integration test for worker process (without real video)."""

import multiprocessing as mp
import tempfile
from pathlib import Path


def simple_worker(queue):
    """Simple worker for testing message protocol."""
    from vidslide.worker import WorkerMessage
    queue.put({"type": WorkerMessage.STARTED})
    queue.put({"type": WorkerMessage.PROGRESS, "progress": 50.0, "message": "Halfway"})
    queue.put({"type": WorkerMessage.DONE, "slides": 5})


def test_worker_message_protocol():
    """Test that worker process can send messages correctly."""
    from vidslide.worker import WorkerMessage

    queue = mp.Queue()
    process = mp.Process(target=simple_worker, args=(queue,))
    process.start()

    # Collect messages
    messages = []
    while process.is_alive() or not queue.empty():
        try:
            msg = queue.get(timeout=0.1)
            messages.append(msg)
        except:
            pass

    process.join(timeout=1.0)

    # Verify messages
    assert len(messages) == 3
    assert messages[0]["type"] == WorkerMessage.STARTED
    assert messages[1]["type"] == WorkerMessage.PROGRESS
    assert messages[1]["progress"] == 50.0
    assert messages[2]["type"] == WorkerMessage.DONE
    assert messages[2]["slides"] == 5

    print("[OK] Worker message protocol works")


def test_cancel_event():
    """Test that cancel event can be set and checked."""
    cancel_event = mp.Event()
    assert not cancel_event.is_set()

    cancel_event.set()
    assert cancel_event.is_set()

    print("[OK] Cancel event works")


def test_fd_redirect():
    """Test that fd-level redirect captures print statements."""
    import sys
    import os

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as f:
        log_path = f.name

    try:
        # Save original
        original_stdout = os.dup(sys.stdout.fileno())

        # Redirect
        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(log_fd, sys.stdout.fileno())
        os.close(log_fd)

        # This should go to the log file
        print("test message")
        sys.stdout.flush()

        # Restore
        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdout)

        # Verify
        with open(log_path, 'r') as f:
            content = f.read()
            assert "test message" in content

        print("[OK] fd-level redirect works")

    finally:
        Path(log_path).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run tests
    test_worker_message_protocol()
    test_cancel_event()
    test_fd_redirect()
    print("\n[OK] All integration tests passed")
