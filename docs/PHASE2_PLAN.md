# Phase 2: Reliable State & Export

> **Phase 1 Complete:** CLI baseline locked, extraction verified with real test data.

---

## Goals

Build on Phase 1's reliable extraction to add:

1. **State validation** - Verify run directory integrity
2. **Export** - Package extracted slides into usable formats
3. **Error recovery** - Handle interrupted or corrupted runs
4. **Resume** - Continue incomplete extractions

---

## Scope

### What We're Building

**1. State Validation (`audit` command basis)**

```bash
vidslide validate RUN
```

- Check manifest.json integrity
- Verify all referenced assets exist
- Validate sequence consistency
- Check events.jsonl completeness
- Report any anomalies

**2. Export Command**

```bash
vidslide export RUN [--format pptx|pdf|images]
```

- Package slides into PPTX (primary format)
- Optional PDF export
- Optional image archive (zip)
- Preserve sequence from manifest
- Include metadata

**3. Resume Capability**

```bash
vidslide extract VIDEO --resume
```

- Detect incomplete runs
- Resume from last successful frame
- Avoid re-extracting existing slides
- Safe restart after interruption

**4. Error Recovery**

- Graceful handling of corrupted manifest
- Asset file recovery
- Partial extraction salvage
- Clear error messages with recovery steps

---

## Non-Goals (Deferred)

**Not in Phase 2:**
- ❌ QA system (Phase 3)
- ❌ AI review (Phase 4)
- ❌ Complex state resolution (Phase 5)
- ❌ `run` one-shot command (Phase 3)
- ❌ Advanced duplicate detection
- ❌ Quality scoring

---

## Implementation Steps

### Step 1: State Validation (2-3 hours)

**Create:** `src/vidslide/validate.py`

**Features:**
- Load and parse manifest.json
- Check schema version compatibility
- Verify all assets in sequence exist on disk
- Validate ULID format for all IDs
- Check events.jsonl parse validity
- Detect orphaned assets (in directory but not in manifest)
- Output structured validation report

**Output format:**
```json
{
  "status": "ok",
  "checks": {
    "manifest_valid": true,
    "assets_complete": true,
    "sequence_valid": true,
    "events_valid": true
  },
  "issues": []
}
```

### Step 2: PPTX Export (4-5 hours)

**Create:** `src/vidslide/export_pptx.py`

**Features:**
- Use `python-pptx` library (already in legacy dependencies)
- Create presentation with slide dimensions matching video aspect ratio
- Add slides in manifest sequence order
- Include title slide with metadata (video name, extraction date, engine)
- Add notes with provenance (source_frame, source_time)
- Handle 16:9 aspect ratio (1920x1080 video)

**Command:**
```bash
vidslide export RUN --format pptx --output OUTFILE.pptx
```

**Implementation notes:**
- Read manifest.json for sequence
- Load assets in order
- Create PPTX with one slide per asset
- Add metadata to presentation properties
- Atomic write (tmp → rename)

### Step 3: Resume Implementation (3-4 hours)

**Modify:** `src/vidslide/extract.py`, `src/vidslide/worker.py`

**Features:**
- Detect existing run directory with state EXTRACTING
- Read last saved asset from manifest
- Calculate `start_frame` and `saved_offset` for legacy engine
- Pass to worker process
- Continue extraction from checkpoint

**Safety:**
- Only resume if state is EXTRACTING (not EXTRACTED or FAILED)
- Verify existing assets before resuming
- Log resume event to events.jsonl
- Handle case where video file changed (SHA256 mismatch)

**New state transitions:**
```
EXTRACTING --[resume]--> EXTRACTING (continue)
EXTRACTING --[complete]--> EXTRACTED
```

### Step 4: Error Recovery (2-3 hours)

**Create:** `src/vidslide/recover.py`

**Features:**
- Detect corrupted manifest (JSON parse error)
- Attempt to reconstruct from events.jsonl
- Salvage partial extractions
- Create recovery report
- Suggest next actions

**Recovery strategies:**
1. Manifest corrupted → reconstruct from events
2. Assets missing → mark as incomplete, suggest re-extract
3. Sequence invalid → rebuild from asset discovery
4. Events incomplete → mark as unreliable audit trail

### Step 5: Testing & Documentation (2-3 hours)

**Test scenarios:**
- Complete export workflow
- Resume after interruption (Ctrl-C mid-extraction)
- Corrupted manifest recovery
- Missing asset handling
- Large video export (>100 slides)

**Documentation:**
- Update GUIDE.md with export workflow
- Document resume mechanism
- Add recovery procedures
- Update validation checks

---

## Acceptance Criteria

### Must Have

1. **validate command works**
   - Detects all common integrity issues
   - Clear, actionable error messages
   - JSON output for agent consumption

2. **PPTX export works**
   - Creates valid PowerPoint file
   - Preserves slide order
   - Includes basic metadata
   - Handles 100+ slide presentations

3. **Resume works**
   - Detects incomplete runs
   - Continues from checkpoint
   - No duplicate slides
   - Safe after interruption

4. **Error recovery guides user**
   - Detects corrupted state
   - Suggests recovery steps
   - Salvages what's possible

### Should Have

- Export to PDF (using pillow or reportlab)
- Image archive export (zip of PNGs)
- Validation warnings for non-critical issues
- Resume with video checksum verification

### Can Defer

- Multiple export formats in one command
- Custom PPTX templates
- Incremental resume (frame-level checkpoint)
- Advanced recovery heuristics

---

## Technical Decisions

### TD-001: PPTX Library Choice

**Decision:** Use `python-pptx`

**Rationale:**
- Already in legacy v0.4.1 dependencies
- Well-documented, stable
- Pure Python, no external deps
- Good enough for basic presentations

**Alternative considered:** ReportLab (for PDF), but PPTX is primary format

### TD-002: Resume Checkpoint Granularity

**Decision:** Resume from last completed slide, not frame-level

**Rationale:**
- Simpler implementation
- Legacy engine doesn't expose frame-level checkpoints easily
- Slide-level is "good enough" for 99-minute videos
- Avoids partial slide issues

**Future:** Could add frame-level checkpoints in Phase 3+

### TD-003: State Recovery Strategy

**Decision:** Reconstruct from events.jsonl, not filesystem scan

**Rationale:**
- events.jsonl is append-only, more reliable than manifest
- Maintains audit trail integrity
- Filesystem scan loses provenance data
- Aligns with "events as source of truth" principle

**Fallback:** Filesystem scan only if events.jsonl also corrupted

---

## Dependencies

**New:**
- None (python-pptx already available)

**Existing:**
- python-pptx (PPTX creation)
- pillow (image handling, optional PDF)

---

## Time Estimate

- Step 1: Validation - 2-3 hours
- Step 2: PPTX Export - 4-5 hours
- Step 3: Resume - 3-4 hours
- Step 4: Recovery - 2-3 hours
- Step 5: Testing - 2-3 hours

**Total:** 13-18 hours

**Optimistic:** 2 working days
**Realistic:** 3 working days

---

## Success Metrics

At Phase 2 completion:

✅ `vidslide export RUN` creates valid PPTX
✅ `vidslide validate RUN` detects all test corruptions
✅ `vidslide extract VIDEO --resume` continues interrupted work
✅ Interrupted extraction (Ctrl-C) is recoverable
✅ Agent can reliably extract → validate → export workflow

---

## Next Phase Preview

**Phase 3: Deterministic QA**
- `audit` command (full implementation)
- Duplicate detection
- Quality checks (blur, blank slides)
- Anomaly flagging

We'll build the QA foundation in Phase 3, then add AI review in Phase 4.

---

_Created: 2025-01-02_
_Phase 1 Completion: 2025-01-02_
