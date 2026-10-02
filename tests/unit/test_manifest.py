"""Unit tests for manifest and run management."""

import tempfile
from pathlib import Path

from vidslide.manifest import Manifest
from vidslide.run import Run
from vidslide.protocol import RunState
from vidslide.ids import generate_id


def test_manifest_creation():
    """Test creating a new manifest."""
    run_id = generate_id("run")
    video_info = {
        "sha256": "abc123",
        "size_bytes": 1000000,
        "video": {
            "duration_seconds": 100.0,
            "fps_reported": 25.0,
            "width": 1920,
            "height": 1080,
        },
    }

    manifest = Manifest.create_new(
        run_id=run_id,
        video_path="/path/to/video.mp4",
        video_info=video_info,
    )

    assert manifest.run_id == run_id
    assert manifest.state == RunState.NEW.value
    assert manifest.revision == 0
    assert len(manifest.sequence) == 0
    assert manifest.data["engine"]["id"] == "legacy-v041"


def test_manifest_add_asset():
    """Test adding an asset to manifest."""
    manifest = Manifest.create_new(
        run_id=generate_id("run"),
        video_path="/video.mp4",
        video_info={"sha256": "abc", "size_bytes": 1000, "video": {}},
    )

    asset_id = generate_id("s")
    manifest.add_asset(
        asset_id=asset_id,
        asset_path=f"assets/{asset_id}.jpg",
        source_frame=1000,
        source_time_seconds=40.0,
    )

    assert asset_id in manifest.assets
    assert asset_id in manifest.sequence
    assert manifest.assets[asset_id]["source_frame"] == 1000
    assert manifest.assets[asset_id]["source_time_seconds"] == 40.0
    assert manifest.revision == 1


def test_manifest_save_and_load():
    """Test saving and loading manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"

        # Create and save
        manifest = Manifest.create_new(
            run_id=generate_id("run"),
            video_path="/video.mp4",
            video_info={"sha256": "abc", "size_bytes": 1000, "video": {}},
        )
        manifest.save(manifest_path, atomic=True)

        # Load
        loaded = Manifest.load(manifest_path)
        assert loaded.run_id == manifest.run_id
        assert loaded.state == manifest.state


def test_run_creation():
    """Test creating a run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test.vidslide"

        video_info = {
            "sha256": "abc123",
            "size_bytes": 1000000,
            "video": {"duration_seconds": 100.0, "fps_reported": 25.0},
        }

        run = Run.create(
            video_path="/path/to/video.mp4",
            video_info=video_info,
            output_dir=str(output_dir),
        )

        # Check directory structure
        assert run.run_dir.exists()
        assert run.assets_dir.exists()
        assert run.candidates_dir.exists()
        assert run.review_dir.exists()
        assert run.qa_dir.exists()
        assert run.logs_dir.exists()

        # Check manifest
        assert run.manifest_path.exists()
        assert run.manifest.state == RunState.NEW.value

        # Check events
        assert run.events_path.exists()
        events = run.events.read_all()
        assert len(events) >= 1
        assert events[0]["type"] == "RUN_CREATED"


def test_id_generation():
    """Test ID generation."""
    from vidslide.ids import generate_id, generate_ulid

    # Test ULID
    ulid1 = generate_ulid()
    ulid2 = generate_ulid()
    assert len(ulid1) == 26
    assert len(ulid2) == 26
    assert ulid1 != ulid2

    # Test prefixed IDs
    run_id = generate_id("run")
    slide_id = generate_id("s")
    assert run_id.startswith("run_")
    assert slide_id.startswith("s_")
    assert len(run_id) == 30  # "run_" + 26 chars
    assert len(slide_id) == 28  # "s_" + 26 chars
