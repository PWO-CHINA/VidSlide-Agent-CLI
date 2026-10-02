"""Stable ID generation for VidSlide assets and entities.

Uses ULID (Universally Unique Lexicographically Sortable Identifier) for
stable, sortable IDs that never change once created.
"""

import time
import random
from typing import Literal

# ULID encoding (Crockford's Base32)
ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_time(timestamp_ms: int, length: int) -> str:
    """Encode timestamp as base32."""
    result = ""
    for _ in range(length):
        result = ENCODING[timestamp_ms & 0x1F] + result
        timestamp_ms >>= 5
    return result


def _encode_random(length: int) -> str:
    """Encode random bytes as base32."""
    result = ""
    for _ in range(length):
        result += ENCODING[random.randint(0, 31)]
    return result


def generate_ulid() -> str:
    """Generate a ULID.

    Format: 01AN4Z07BY79KA1307SR9X4MV3
    - 10 chars: timestamp (milliseconds)
    - 16 chars: randomness

    Returns:
        26-character ULID string
    """
    timestamp_ms = int(time.time() * 1000)
    time_part = _encode_time(timestamp_ms, 10)
    random_part = _encode_random(16)
    return time_part + random_part


def generate_id(
    prefix: Literal["run", "s", "c", "f", "a", "exp", "evt"]
) -> str:
    """Generate a prefixed ID for different entity types.

    Args:
        prefix: Entity type prefix
            - run: extraction run
            - s: slide asset
            - c: candidate asset
            - f: QA flag
            - a: resolution action
            - exp: export artifact
            - evt: event

    Returns:
        Prefixed ID like "s_01AN4Z07BY79KA1307SR9X4MV3"
    """
    ulid = generate_ulid()
    return f"{prefix}_{ulid}"


__all__ = ["generate_id", "generate_ulid"]
