"""VidSlide Agent CLI - AI-native PPT extraction from screen recordings.

This package provides a command-line interface for AI agents to extract
PowerPoint slides from video recordings with reliable state management,
immutable assets, and structured output protocols.
"""

__version__ = "0.1.0"
__engine_baseline__ = "legacy-v041"
__baseline_commit__ = "66ec86808443509df86fbc8d82e5188d8eb90ffc"

from vidslide.protocol import ProtocolVersion

PROTOCOL_VERSION = ProtocolVersion.V1

__all__ = [
    "__version__",
    "__engine_baseline__",
    "__baseline_commit__",
    "PROTOCOL_VERSION",
]
