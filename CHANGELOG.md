# Changelog

All notable changes to VidSlide Agent CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-02

### Added

#### Phase 1: Core Extraction & Worker Isolation
- `capabilities` command - System capabilities check with OpenCV/NumPy/python-pptx validation
- `doctor` command - Environment validation and dependency checks
- `probe` command - Video file analysis without extraction
- `extract` command - Worker-isolated slide extraction preserving v0.4.1 baseline
- Zero-modification integration of VidSlide v0.4.1 engine (commit 66ec868)
- Worker process isolation for reliable extraction
- Structured JSON output protocol for AI agent consumption

#### Phase 2: Reliable State & Export
- `validate` command - Multi-level integrity checks (manifest, assets, events)
- `export` command - PPTX generation with metadata and timestamps
- `recover` command - Corruption recovery and manifest rebuild
- Manifest-based mutable state management
- Events.jsonl immutable audit log
- Asset immutability guarantees

#### Phase 3: QA & Workflow Automation
- `context` command - Temporal slide analysis with gap detection
- `overview` command - Human-readable run summaries with quality indicators
- `audit` command - Complete provenance tracking and history
- `resolve` command - Interactive ambiguity resolution with 4 action types
  - remove_from_sequence: Remove slides
  - insert_into_sequence: Add slides at position
  - accept_gap: Mark temporal gaps as intentional
  - mark_duplicate: Handle duplicate slides
- Semantic slide context for agent decision-making
- Coverage statistics and quality metrics

#### Documentation
- Complete README with quick start and command reference
- GUIDE.md with architecture and design principles
- AGENTS.md with agent behavior rules
- Phase completion reports (Phase 1, 2, 3)
- Implementation status tracking
- Deployment documentation

#### Testing
- Real-world validation: 99-minute lecture video, 27 slides extracted
- Engine integrity smoke tests
- Worker integration tests
- Unit tests for core modules

### Technical Details

**Architecture:**
- Zero engine modifications (v0.4.1 baseline preserved)
- Worker process isolation
- Dual-state model: manifest.json (mutable) + events.jsonl (immutable)
- Immutable asset files
- Structured JSON output on stdout
- Errors on stderr with proper exit codes

**Code Statistics:**
- 13 commands implemented
- 21 core Python modules
- ~3,200 lines of new code
- 0 lines of engine modifications
- 12 documentation files

**Dependencies:**
- Python >=3.8
- opencv-python >=4.5.0
- numpy >=1.20.0
- python-pptx >=0.6.21

### Known Limitations
- Single video processing (no batch operations)
- Local filesystem only
- CLI only (no GUI)
- Minimal test coverage (per project constraints)

### Security
- No network operations
- No external API calls
- Local file processing only
- Sandbox-safe worker isolation

---

## [Unreleased]

### Planned Features (Phase 4 - Optional)
- One-shot command for simplified workflow
- Batch operations for multiple videos
- Advanced duplicate detection with perceptual hashing
- Performance profiling
- Interactive TUI
- Cloud storage integration

---

[0.1.0]: https://github.com/PWO-CHINA/VidSlide-Agent-CLI/releases/tag/v0.1.0
