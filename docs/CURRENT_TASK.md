# Current Task: Phase 3 Planning

**Last Updated:** 2025-01-XX  
**Status:** Phase 2 Complete, Planning Phase 3

---

## Phase 2 Status: ✓ COMPLETE

All Phase 2 deliverables implemented:
- ✓ State validation (`validate` command)
- ✓ PPTX export (`export` command)
- ✓ Resume capability (--resume flag)
- ✓ Error recovery (`recover` command)
- ✓ CLI integration and documentation

See [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) for details.

---

## Phase 3: QA & Agent Workflow Commands

**Goal:** Enable AI agents to perform quality assurance and resolve ambiguities in extracted runs.

### Scope Overview

Phase 3 adds commands for:
1. **Context-aware QA** - Provide agents with semantic context about slides
2. **Overview generation** - Summarize runs for quick understanding
3. **Audit trails** - Detailed provenance and decision history
4. **Resolve workflow** - Interactive ambiguity resolution

### Estimated Effort: 15-20 hours

---

## Step 1: Context Command (4-5 hours)

**Purpose:** Give agents semantic context about extracted slides for QA tasks.

**Command:**
```bash
vidslide context RUN_DIR [--slide INDEX] [--format text|json]
```

**Output (JSON):**
```json
{
  "run_id": "run_xxx",
  "slide_count": 27,
  "duration_seconds": 5940.5,
  "fps": 30.0,
  "slides": [
    {
      "index": 0,
      "asset_id": "a_xxx",
      "source_frame": 1234,
      "source_time": "20m 34.5s",
      "time_since_previous": null,
      "filename": "slide_0000.jpg"
    }
  ],
  "statistics": {
    "avg_time_between_slides": 220.0,
    "min_time_between_slides": 45.2,
    "max_time_between_slides": 890.1,
    "coverage_percentage": 8.2
  }
}
```

**Implementation:**
- File: `src/vidslide/context.py`
- Read manifest and compute temporal statistics
- Flag potential issues (too close, too far apart)
- Provide time-based navigation hints

**Use Case:** Agent asks "Show me slides from the first 10 minutes" or "Which slides are suspiciously close together?"

---

## Step 2: Overview Command (3-4 hours)

**Purpose:** Generate human-readable summaries of runs for quick triage.

**Command:**
```bash
vidslide overview RUN_DIR [--verbose]
```

**Output (JSON):**
```json
{
  "run_id": "run_xxx",
  "video": {
    "filename": "lecture.mp4",
    "duration": "1h 39m 0.5s",
    "resolution": "1920x1080",
    "fps": 30.0,
    "size_mb": 2341.5
  },
  "extraction": {
    "engine": "legacy-v041",
    "profile": "reliable",
    "started_at": "2025-01-15T10:30:00Z",
    "completed_at": "2025-01-15T10:45:23Z",
    "duration": "15m 23s",
    "slide_count": 27,
    "state": "EXTRACTED"
  },
  "quality_indicators": {
    "coverage": "8.2%",
    "avg_slide_duration": "3m 40s",
    "potential_issues": []
  },
  "next_actions": [
    "vidslide validate run_xxx",
    "vidslide export run_xxx"
  ]
}
```

**Implementation:**
- File: `src/vidslide/overview.py`
- Aggregate data from manifest and events
- Calculate quality indicators
- Suggest next actions based on state

**Use Case:** Agent needs to quickly understand a run's status without parsing full manifest.

---

## Step 3: Audit Command (4-5 hours)

**Purpose:** Provide detailed provenance and decision history for compliance/debugging.

**Command:**
```bash
vidslide audit RUN_DIR [--event-type TYPE] [--asset-id ID]
```

**Output (JSON):**
```json
{
  "run_id": "run_xxx",
  "audit_trail": [
    {
      "timestamp": "2025-01-15T10:30:00Z",
      "event": "EXTRACTION_STARTED",
      "data": {
        "engine": "legacy-v041",
        "video_sha256": "abc123..."
      }
    },
    {
      "timestamp": "2025-01-15T10:30:15Z",
      "event": "ASSET_CREATED",
      "data": {
        "asset_id": "a_xxx",
        "source_frame": 1234,
        "filename": "slide_0000.jpg"
      }
    }
  ],
  "summary": {
    "total_events": 32,
    "event_types": {
      "EXTRACTION_STARTED": 1,
      "ASSET_CREATED": 27,
      "EXTRACTION_COMPLETED": 1
    }
  }
}
```

**Implementation:**
- File: `src/vidslide/audit.py`
- Parse and filter events.jsonl
- Provide timeline reconstruction
- Support filtering by event type or asset

**Use Case:** Agent debugging asks "What happened between slide 5 and slide 6?" or "Show me all events for asset a_xxx"

---

## Step 4: Resolve Workflow (5-6 hours)

**Purpose:** Interactive workflow for resolving ambiguities (duplicates, missing slides, ordering issues).

**Command:**
```bash
vidslide resolve RUN_DIR --issue ISSUE_ID --action ACTION
```

**Workflow:**
1. Agent runs `validate` → detects issues
2. Agent examines context with `context` command
3. Agent decides resolution action
4. Agent calls `resolve` with structured action

**Example Actions:**
```json
{
  "issue_id": "duplicate_slides_5_6",
  "action": "remove",
  "target": "a_12345",
  "reason": "Identical to previous slide"
}
```

```json
{
  "issue_id": "missing_slide_gap",
  "action": "accept",
  "reason": "Long pause between topics, gap is intentional"
}
```

**Implementation:**
- File: `src/vidslide/resolve.py`
- Validate issue exists
- Apply action (update manifest, log event)
- Preserve history (never delete assets, only update sequence)

**Use Case:** Agent finds duplicate slides and removes them from sequence, or accepts a gap as intentional.

---

## Phase 3 Principles

**Maintain Phase 1+2 Constraints:**
- ✓ No engine modifications
- ✓ No direct asset manipulation
- ✓ Structured JSON output
- ✓ Immutable events log
- ✓ State transitions tracked

**New Principles:**
- **Agent-first API:** Commands designed for programmatic consumption
- **Semantic richness:** Provide temporal/spatial context, not just file paths
- **Reversible operations:** Resolve actions can be undone via event replay
- **Audit by default:** Every resolve action logged to events

---

## Implementation Order

**Week 1:**
1. Context command (understand what was extracted)
2. Overview command (quick triage)

**Week 2:**
3. Audit command (provenance tracking)
4. Resolve workflow (ambiguity resolution)

**Testing Strategy (Minimal):**
- Unit tests for JSON structure validation
- One golden test per command with test_video.vidslide
- Manual agent workflow verification

---

## Success Criteria

Phase 3 is complete when:
- [ ] All 4 commands implemented and integrated
- [ ] Structured JSON output for all commands
- [ ] Agent can perform full QA workflow:
  1. Extract → 2. Validate → 3. Context → 4. Resolve → 5. Export
- [ ] Documentation updated
- [ ] No regressions in Phase 1+2 functionality

---

## Future Phases (Not Phase 3)

**Phase 4: Batch Operations**
- Process multiple videos in parallel
- Aggregate results
- Comparative QA across runs

**Phase 5: Advanced Recovery**
- Asset corruption detection
- Frame-level recovery
- Checkpointing during extraction

**Phase 6: Performance**
- Profiling tools
- Optimization recommendations
- GPU utilization monitoring

---

## Current Decision Point

**Ready to start Phase 3?**
- Phase 2 is complete and stable
- Commands are well-scoped
- Implementation path is clear
- Estimated effort is reasonable (15-20 hours)

**Alternative: Defer Phase 3 until needed**
- Current tooling may be sufficient for immediate agent tasks
- Could wait for real-world usage to drive requirements
- Focus on stabilization and documentation instead

**Recommendation:** Start Phase 3 Step 1 (Context command) to validate the approach, then reassess.
