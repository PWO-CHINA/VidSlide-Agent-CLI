# Phase 1 Progress Tracker

## Overview

**Phase:** Baseline Lock + Agent-native CLI Core  
**Started:** 2025-01-02  
**Current Status:** Step 6/7 Complete - Extract Integration Done

---

## Completion Status

### ✅ Step 1: Project Structure (COMPLETE)
- [x] Package structure established
- [x] CLI entrypoint with argparse
- [x] `capabilities` command implemented
- [x] `doctor` command implemented
- [x] Error definitions and protocol models
- [x] Helper script (vidslide.sh) created

**Commit:** eb2764e

### ✅ Step 2: Baseline Lock (COMPLETE)
- [x] Legacy v0.4.1 engine copied (byte-identical)
- [x] SHA256 integrity test created
- [x] Engine analysis completed (no Flask deps, clean callbacks)
- [x] Profile parameters confirmed

**Commit:** 3204186, 7f39365

### ✅ Step 3: Run Directory and State (COMPLETE)
- [x] Run directory structure implemented
- [x] ULID-based stable ID generation
- [x] manifest.json atomic writes (.tmp → rename)
- [x] events.jsonl append-only logging
- [x] State machine (13 states)

**Commit:** eb2764e

### ✅ Step 4: Worker Isolation (COMPLETE)
- [x] Multiprocessing worker wrapper
- [x] fd-level stdout/stderr redirect (os.dup2)
- [x] Message queue IPC
- [x] Sticky cancel with mp.Event
- [x] Progress event forwarding

**Commit:** eb2764e, 7f39365

### ✅ Step 5: Probe Command (COMPLETE)
- [x] File existence check
- [x] OpenCV video probe
- [x] First frame decode smoke test
- [x] Pre-flight validation (fps > 0, frames >= 10)
- [x] SHA256 hash computation
- [x] JSONL output

**Commit:** eb2764e, 7f39365

### ✅ Step 6: Extract Command (COMPLETE)
- [x] Legacy engine integration via worker
- [x] on_progress callback adapter with throttling
- [x] SLIDE_SAVED detection (saved count delta)
- [x] Immutable asset creation
- [x] Manifest updates with provenance
- [x] Event logging (ASSET_CREATED)
- [x] Terminal message handling (DONE/ERROR)
- [x] State transitions (NEW → EXTRACTING → EXTRACTED)
- [x] Parameter mapping (decoder → use_gpu, speed_mode whitelist)

**Commit:** 7f39365

### ⏳ Step 7: Golden Regression (BLOCKED - NO OPENCV)
- [ ] Create synthetic test video
- [ ] End-to-end extract test
- [ ] Golden baseline recording
- [ ] Regression test suite
- [ ] CI integration

**Blocker:** OpenCV not installed in environment

---

## Implementation Details

### Worker Integration (Step 6)

**Key Changes:**
- **worker.py:** ~130 LOC modified
  - Real `extract_slides` call with lazy import
  - fd-level redirect (not Python-level)
  - on_progress adapter with 0.5s throttle
  - Slide detection via saved count delta
  - Sticky cancel via mp.Event
  - Parameter mapping and validation

- **extract.py:** ~50 LOC modified
  - Fixed message loop (drain until terminal)
  - SLIDE_SAVED → manifest.add_asset()
  - Provenance: source_frame, source_time_seconds
  - Pass fps to worker via params["_fps"]

- **probe.py:** ~6 LOC modified
  - Pre-flight: fps > 0, frames >= 10
  - Added fps to result for worker

### Engine Integrity

**SHA256 (LF-normalized):**
```
b558496290b9dd4af4e277af8736a274200d30d72a99c3393e46dfc429bbc3b4
```

**Verification:** ✅ PASS (test_engine_integrity.py)

**Modifications to Engine:** 0 lines

---

## Next Steps

### Immediate (Requires OpenCV)

1. Install OpenCV dependencies:
   ```bash
   pip install opencv-python numpy
   ```

2. Create synthetic test video:
   - 10fps, total 26 seconds
   - Scene A (5s) → fade (1s) → Scene B (5s) → Scene C (5s) → Scene A (5s) → Scene D (0.8s)
   - Expected: 3 slides (history on), 4 slides (history off)

3. End-to-end test:
   ```bash
   vidslide extract test_video.mp4
   ```

4. Verify:
   - stdout is pure JSONL
   - manifest.json has correct asset count
   - assets/ has PNG files
   - provenance is recorded
   - events.jsonl is complete

### After Testing

5. Golden baseline:
   - Record expected output
   - Store in tests/golden/
   - Create regression test

6. Documentation:
   - Update GUIDE.md with actual usage
   - Record any discovered issues
   - Document parameter behavior

---

## Known Issues

### Resolved
- ✅ Flask dependency myth (was never there)
- ✅ Stdout pollution (fd-level redirect)
- ✅ One-shot cancel (now sticky with mp.Event)
- ✅ Progress callback args (all 6 always passed)

### Open
- ⚠️ OpenCV not installed (blocks testing)
- ⚠️ Resume not implemented (deferred to Phase 2)
- ⚠️ Cancel signal handling (Ctrl-C) not wired to worker

---

## Deferred to Later Phases

**Phase 2:**
- Resume mechanism
- Graceful Ctrl-C handling
- State recovery validation

**Phase 4:**
- QA system
- Quality assessment
- Duplicate detection improvements

**Phase 5:**
- overview/context/recover commands
- resolve command
- State resolution

---

## Time Spent

- **Step 1-5:** ~2 hours (infrastructure)
- **Step 6:** ~1.5 hours (integration)
- **Subagent analysis:** ~20 minutes (saved ~2 hours of debugging)

**Total:** ~3.5 hours (vs estimated 4-5 hours)

---

_Last Updated: 2025-01-02 21:15_
