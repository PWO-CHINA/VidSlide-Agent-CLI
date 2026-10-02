# VidSlide Agent CLI v0.1.0 Release Notes

**Release Date:** October 2, 2026  
**Repository:** https://github.com/PWO-CHINA/VidSlide-Agent-CLI

---

## 🎉 What's New

VidSlide Agent CLI v0.1.0 is the first production release of an AI-native command-line tool for extracting PowerPoint slides from screen recordings. Built on the reliable VidSlide v0.4.1 engine with zero modifications to the extraction logic.

## ✨ Key Features

### Complete Workflow Automation (13 Commands)

**Extraction Pipeline:**
- `probe` - Analyze video files without extraction
- `extract` - Extract slides with worker isolation
- `validate` - Run integrity checks
- `export` - Generate PowerPoint files

**Quality Assurance:**
- `context` - Temporal slide analysis
- `overview` - Quality metrics and summaries
- `audit` - Complete provenance tracking
- `resolve` - Interactive ambiguity resolution

**System Management:**
- `capabilities` - Check system requirements
- `doctor` - Validate environment
- `recover` - Fix corrupted runs

### AI-Native Design

- **Structured JSON Output:** All commands output machine-readable JSON on stdout
- **Semantic Context:** Provides temporal analysis and quality indicators for agent decision-making
- **Complete Provenance:** Immutable audit log (events.jsonl) tracks all operations
- **Reversible Operations:** Manifest-based state allows undo/redo

### Production-Ready Architecture

- **Zero Engine Modifications:** v0.4.1 extraction baseline preserved
- **Worker Isolation:** Robust process isolation prevents corruption
- **Immutable Assets:** Extracted images never modified
- **Dual-State Model:** Mutable manifest + immutable event log

## 📊 Real-World Validation

Successfully tested with:
- 99-minute lecture video
- 27 slides extracted
- All commands verified end-to-end
- JSON protocol validated
- Worker isolation confirmed

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/PWO-CHINA/VidSlide-Agent-CLI.git
cd VidSlide-Agent-CLI

# Install dependencies
pip install opencv-python numpy python-pptx

# Verify installation
python src/vidslide/cli.py doctor
```

### Basic Usage

```bash
# Extract slides from video
python src/vidslide/cli.py extract lecture.mp4

# Validate extraction
python src/vidslide/cli.py validate lecture.vidslide

# Get quality overview
python src/vidslide/cli.py overview lecture.vidslide

# Export to PowerPoint
python src/vidslide/cli.py export lecture.vidslide
```

### Agent Usage

```bash
# Get semantic context for decision-making
python src/vidslide/cli.py context lecture.vidslide

# Review audit trail
python src/vidslide/cli.py audit lecture.vidslide

# Resolve ambiguities programmatically
python src/vidslide/cli.py resolve lecture.vidslide \
  --action '{"type":"remove_from_sequence","asset_id":"slide_0005"}'
```

## 📚 Documentation

- **[README.md](README.md)** - Complete user guide
- **[GUIDE.md](GUIDE.md)** - Architecture and design principles
- **[AGENTS.md](AGENTS.md)** - AI agent usage rules
- **[CHANGELOG.md](CHANGELOG.md)** - Full change history

## 🎯 Design Principles

1. **Reliability Over Features** - Stable behavior, clear errors, reversible operations
2. **Zero Engine Modifications** - v0.4.1 extraction logic untouched
3. **Avoid Over-Engineering** - No database, no message queue, simple file-based state
4. **Agent-Native** - Structured output, complete provenance, semantic context

## 🔧 Technical Specifications

### Requirements
- Python 3.8 or higher
- OpenCV (opencv-python) >= 4.5.0
- NumPy >= 1.20.0
- python-pptx >= 0.6.21

### Output Format
```
VIDEO.vidslide/
├── manifest.json          # Mutable state snapshot
├── events.jsonl          # Immutable audit log
└── assets/               # Immutable extracted slides
    ├── slide_0000.jpg
    ├── slide_0001.jpg
    └── ...
```

### Code Statistics
- **Commands:** 13
- **Modules:** 21 Python files
- **New Code:** ~3,200 LOC
- **Engine Modified:** 0 LOC

## ⚠️ Known Limitations

- Single video processing (no batch operations)
- Local filesystem only
- CLI only (no GUI)
- Minimal test coverage (per project design constraints)

## 🔮 Future Enhancements (Optional Phase 4)

The following features are planned but not required for production:

1. **One-shot command** - Single command for extract+validate+export
2. **Batch operations** - Process multiple videos
3. **Advanced duplicate detection** - Perceptual hashing
4. **Performance profiling** - Identify bottlenecks
5. **Interactive TUI** - Visual slide browser
6. **Cloud storage** - S3/GCS integration

These will be prioritized based on user feedback and real-world usage patterns.

## 🐛 Bug Reports

Please report issues at: https://github.com/PWO-CHINA/VidSlide-Agent-CLI/issues

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Credits

Built on [VidSlide v0.4.1](https://github.com/PWO-CHINA/VidSlide) by PWO-CHINA.

Agent CLI architecture designed for AI-native consumption by Claude Code, Codex, and automated workflows.

## 🔗 Links

- **Repository:** https://github.com/PWO-CHINA/VidSlide-Agent-CLI
- **Issues:** https://github.com/PWO-CHINA/VidSlide-Agent-CLI/issues
- **Original VidSlide:** https://github.com/PWO-CHINA/VidSlide

---

**Install now:**
```bash
git clone https://github.com/PWO-CHINA/VidSlide-Agent-CLI.git
```

**Happy extracting! 🎬➡️📊**
