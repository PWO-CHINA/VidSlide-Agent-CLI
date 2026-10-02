"""Capabilities query for VidSlide Agent CLI.

Declares supported commands, engines, export formats, and optional features.
"""

from vidslide.protocol import ProtocolVersion


def get_capabilities() -> dict:
    """Return the capabilities of this VidSlide CLI instance.

    Returns a dict suitable for JSON serialization describing:
    - Protocol version
    - Supported commands
    - Available engines
    - Export formats
    - Optional capabilities

    Returns:
        dict: Capabilities manifest with protocol_version, commands, engines,
              export_formats, and optional_capabilities.
    """
    return {
        "protocol_version": ProtocolVersion.V1.value,
        "commands": [
            "probe",
            "extract",
            "audit",
            "overview",
            "context",
            "recover",
            "resolve",
            "export",
            "run",
            "doctor",
        ],
        "engines": [
            {
                "id": "legacy-v041",
                "recommended": True,
            }
        ],
        "export_formats": [
            "pdf",
            "pptx",
            "zip",
        ],
        "optional_capabilities": {
            "page_number_ocr": False,
        },
    }


__all__ = [
    "get_capabilities",
]
