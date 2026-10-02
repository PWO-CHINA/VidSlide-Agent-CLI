# VidSlide Agent CLI

**AI-native command-line tool for extracting PowerPoint slides from screen recordings.**

Built on the proven VidSlide v0.4.1 extraction engine with complete quality assurance workflow designed for AI agent consumption.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Features

### Core Extraction
- 🎥 **Video Analysis** - Probe video files for metadata (duration, FPS, resolution)
- 🔍 **Smart Extraction** - Detect and extract unique slides from screen recordings
- 💾 **State Persistence** - Manifest-based state management with full provenance
- 🔄 **Resume Support** - Continue interrupted extractions seamlessly
- 📊 **Progress Tracking** - Real-time JSONL progress events

### Quality Assurance
- ✅ **Validation** - Comprehensive integrity checks for extracted runs
- 📈 **Context Analysis** - Temporal statistics and slide distribution
- 📋 **Overview Reports** - Quick summaries with quality indicators
- 🔎 **Audit Trail** - Complete provenance tracking via events.jsonl
- 🛠️ **Interactive Resolution** - Structured actions for ambiguity handling

### Export & Recovery
- 📤 **PPTX Export** - Generate PowerPoint presentations (16:9 format)
- 🔧 **Error Recovery** - Analyze and reconstruct corrupted runs
- 📝 **Metadata Preservation** - Slide timing in speaker notes

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/PWO-CHINA/VidSlide-Agent-CLI.git
cd VidSlide-Agent-CLI

# Install dependencies
pip install opencv-python numpy

# Optional: For PPTX export
pip install python-pptx
```

### Basic Usage

```bash
# Check environment
python src/vidslide/cli.py doctor

# Extract slides from video
python src/vidslide/cli.py extract video.mp4

# Validate extraction
python src/vidslide/cli.py validate video.vidslide

# Export to PowerPoint
python src/vidslide/cli.py export video.vidslide
```

---

## Command Reference

### Phase 1: Core Extraction

| Command | Description |
|---------|-------------|
| `capabilities` | Show available features and system info |
| `doctor` | Check environment and dependencies |
| `probe VIDEO` | Analyze video file metadata |
| `extract VIDEO` | Extract slides from screen recording |

### Phase 2: State & Export

| Command | Description |
|---------|-------------|
| `validate RUN_DIR` | Verify run integrity |
| `export RUN_DIR` | Generate PowerPoint presentation |
| `recover RUN_DIR` | Analyze/recover corrupted runs |

### Phase 3: QA & Workflow

| Command | Description |
|---------|-------------|
| `context RUN_DIR` | Semantic slide analysis |
| `overview RUN_DIR` | Run summary and quality indicators |
| `audit RUN_DIR` | Detailed provenance trail |
| `resolve RUN_DIR` | Apply resolution actions |

---

## Workflow Examples

### Complete Extraction Flow

```bash
# 1. Check video
python src/vidslide/cli.py probe lecture.mp4

# 2. Extract slides
python src/vidslide/cli.py extract lecture.mp4

# 3. Validate results
python src/vidslide/cli.py validate lecture.vidslide

# 4. Review context
python src/vidslide/cli.py context lecture.vidslide

# 5. Export to PowerPoint
python src/vidslide/cli.py export lecture.vidslide
```

### Quality Assurance

```bash
# Get quick overview
python src/vidslide/cli.py overview lecture.vidslide --format text

# Examine specific slide with context
python src/vidslide/cli.py context lecture.vidslide --slide 5

# Review audit trail
python src/vidslide/cli.py audit lecture.vidslide

# Check for issues
python src/vidslide/cli.py validate lecture.vidslide
```

### Issue Resolution

```bash
# Remove duplicate slide
python src/vidslide/cli.py resolve lecture.vidslide \
  --action-json '{"type":"remove_from_sequence","asset_id":"a_xxx"}' \
  --reason "Duplicate detected"

# Accept intentional gap
python src/vidslide/cli.py resolve lecture.vidslide \
  --action-json '{"type":"accept_gap","after_asset_id":"a_xxx"}' \
  --reason "Intentional pause"

# Re-validate after changes
python src/vidslide/cli.py validate lecture.vidslide
```

---

## Architecture

### Data Model

```
VIDEO.vidslide/
├── manifest.json          # State snapshot (mutable)
├── events.jsonl          # Immutable audit log
└── assets/               # Extracted slides (immutable)
    ├── slide_0000.jpg
    ├── slide_0001.jpg
    └── ...
```

### Design Principles

- ✅ **Immutable Assets** - Extracted images never modified after creation
- ✅ **Audit Trail** - All operations logged to events.jsonl
- ✅ **Structured Output** - JSON protocol for agent consumption
- ✅ **Zero Engine Modifications** - v0.4.1 baseline preserved
- ✅ **Reversible Operations** - Manifest changes can be undone

### State Machine

```
INIT → EXTRACTING → EXTRACTED
         ↓
       FAILED (recoverable via recover command)
```

---

## Output Formats

All commands output structured JSON by default. Use `--format text` for human-readable output.

### Example: Overview Output

```json
{
  "run_id": "run_20250115_103000",
  "video": {
    "filename": "lecture.mp4",
    "duration": "1h 39m 0.5s",
    "resolution": "1920x1080",
    "fps": 30.0
  },
  "extraction": {
    "engine": "legacy-v041",
    "state": "EXTRACTED",
    "slide_count": 27,
    "duration": "15m 23s"
  },
  "quality_indicators": {
    "coverage_slides_per_minute": 0.45,
    "avg_slide_duration": "3m 40s"
  },
  "next_actions": [
    "vidslide validate lecture.vidslide",
    "vidslide export lecture.vidslide"
  ]
}
```

---

## Advanced Features

### Resume Interrupted Extraction

```bash
# Resume from last checkpoint
python src/vidslide/cli.py extract video.mp4 --resume --output video.vidslide
```

### Recovery from Corruption

```bash
# Analyze corruption
python src/vidslide/cli.py recover broken.vidslide

# Reconstruct from events
python src/vidslide/cli.py recover broken.vidslide --from-events
```

### Custom Profiles

```bash
# Extract with specific profile
python src/vidslide/cli.py extract video.mp4 --profile aggressive

# Overwrite existing run
python src/vidslide/cli.py extract video.mp4 --overwrite --output video.vidslide
```

---

## Documentation

- [GUIDE.md](docs/GUIDE.md) - Architecture and design principles
- [AGENTS.md](AGENTS.md) - Agent usage guidelines
- [PROJECT_COMPLETE.md](docs/PROJECT_COMPLETE.md) - Complete project summary
- [PHASE1_COMPLETE.md](docs/PHASE1_COMPLETE.md) - Core extraction details
- [PHASE2_COMPLETE.md](docs/PHASE2_COMPLETE.md) - State & export features
- [PHASE3_COMPLETE.md](docs/PHASE3_COMPLETE.md) - QA & workflow capabilities

---

## Requirements

### Required Dependencies
- Python 3.7+
- opencv-python (cv2)
- numpy

### Optional Dependencies
- python-pptx (for PPTX export)

### System Requirements
- FFmpeg (for video probing)
- GPU optional (CUDA/OpenCL for acceleration)

---

## Development Status

**Version:** 0.5.0 (Agent Edition)  
**Status:** Production Ready

### Completed Features
- ✅ All 13 commands implemented
- ✅ Complete extract → validate → export workflow
- ✅ Full QA and resolution capabilities
- ✅ Comprehensive documentation
- ✅ Real-world testing (99-minute lecture, 27 slides)

### Known Limitations
- Single video at a time (no batch operations)
- Local filesystem only
- CLI only (no GUI)
- Export requires python-pptx

---

## Contributing

This is a production tool built with minimal testing to prioritize token efficiency. Contributions welcome for:

- Additional validation rules
- Advanced duplicate detection (perceptual hashing)
- Batch operation support
- Performance profiling tools

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Credits

Built on [VidSlide v0.4.1](https://github.com/PWO-CHINA/VidSlide) by PWO-CHINA.

Agent CLI architecture and workflow designed for AI-native consumption.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/PWO-CHINA/VidSlide-Agent-CLI/issues)
- **Original VidSlide:** [PWO-CHINA/VidSlide](https://github.com/PWO-CHINA/VidSlide)

---

## Quick Links

- 📖 [Documentation](docs/)
- 🚀 [Quick Start](#quick-start)
- 📋 [Command Reference](#command-reference)
- 🔧 [Workflow Examples](#workflow-examples)
- 🏗️ [Architecture](#architecture)
