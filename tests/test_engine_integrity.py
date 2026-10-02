"""Test that legacy engine file remains byte-identical to v0.4.1 baseline."""

import hashlib
from pathlib import Path


def test_engine_file_integrity():
    """Verify legacy_v041_original.py matches the v0.4.1 baseline (LF-normalized)."""
    engine_path = Path("src/vidslide/engine/legacy_v041_original.py")

    # Read and normalize line endings
    with open(engine_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Normalize to LF
    content_lf = content.replace("\r\n", "\n").replace("\r", "\n")

    # Compute SHA256
    sha256 = hashlib.sha256(content_lf.encode("utf-8")).hexdigest()

    # Expected hash from v0.4.1 baseline (commit 66ec86808443509df86fbc8d82e5188d8eb90ffc)
    EXPECTED_SHA256 = "b558496290b9dd4af4e277af8736a274200d30d72a99c3393e46dfc429bbc3b4"

    assert sha256 == EXPECTED_SHA256, (
        f"Engine file has been modified!\n"
        f"Expected: {EXPECTED_SHA256}\n"
        f"Got:      {sha256}\n"
        f"The legacy engine must remain byte-identical to v0.4.1 baseline."
    )


if __name__ == "__main__":
    test_engine_file_integrity()
    print("[OK] Engine integrity verified")
