# Legacy Engine Integration - Complete

## Summary

Successfully integrated the VidSlide v0.4.1 legacy extraction engine into the worker process without modifying the engine code. The integration is complete and ready for testing with real video files.

---

## What Was Done

### 1. Engine Analysis (Subagent)

**Key Discovery:** The legacy engine has **zero dependencies on Flask** and uses a clean callback interface. Previous assumptions were incorrect.

- Signature: `extract_slides(video_path, output_dir, ..., on_progress=None, should_cancel=None)`
- Callbacks: `on_progress(saved, pct, message, eta_s, elapsed_s, current_frame)` - all 6 args always passed
- Returns: `(status, message, saved)` where status is 'done'/'cancelled'/'error'
- 10 print() statements captured by stdout redirect

**SHA256 (LF-normalized):**
```
b558496290b9dd4af4e277af8736a274200d30d72a99c3393e46dfc429bbc3b4
```

### 2. Worker Process Implementation

**File:** `src/vidslide/worker.py` (~130 LOC modified)

**Key Features:**
- **fd-level redirect:** Uses `os.dup2()` to capture stdout/stderr at file descriptor level
- **Lazy import:** Imports `extract_slides` only in worker process to avoid loading cv2 in parent
- **on_progress adapter:** Converts engine callbacks to message queue events
- **SLIDE_SAVED detection:** Monitors `saved` count delta to emit asset creation events
- **Sticky cancel:** Uses `mp.Event` so cancel persists across polling calls
- **Parameter mapping:**
  - `decoder: "auto"/"cpu"/"gpu"` → `use_gpu: bool`
  - `speed_mode` whitelist: only "eco" or "fast" (blocks "turbo")
- **Progress throttling:** 0.5 second minimum between progress updates

### 3. Extract Command Enhancement

**File:** `src/vidslide/extract.py` (~50 LOC modified)

**Key Features:**
- **Fixed message loop:** Drains queue until terminal message (DONE/ERROR), not just `is_alive()`
- **SLIDE_SAVED handling:** Creates asset with ULID, adds to manifest with provenance
- **Provenance calculation:** 
  - `source_frame` from callback
  - `source_time_seconds = source_frame / fps`
- **Atomic manifest updates:** Save after each asset creation
- **Event logging:** ASSET_CREATED events to events.jsonl
- **Pass fps to worker:** Via `params["_fps"]` for provenance calculation

### 4. Probe Enhancement

**File:** `src/vidslide/probe.py` (~6 LOC modified)

**Key Features:**
- **Pre-flight validation:** fps > 0, frame_count >= 10 (parity with GUI)
- **Return fps:** Added to probe result for worker use

### 5. Testing

**Files Created:**
- `tests/test_engine_integrity.py` - SHA256 verification (PASS ✓)
- `tests/test_worker_integration.py` - Message protocol, cancel, fd-redirect (PASS ✓)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Parent Process (extract.py)                                 │
│                                                              │
│  ┌────────────┐      ┌──────────────┐                      │
│  │ probe      │──1──▶│ Run.create() │                      │
│  └────────────┘      └──────────────┘                      │
│                             │                                │
│                             ▼                                │
│              ┌────────────────────────────┐                 │
│              │ ExtractionWorker.start()   │                 │
│              └────────────────────────────┘                 │
│                             │                                │
│                             ▼                                │
│              ┌────────────────────────────┐                 │
│              │ mp.Process spawn           │                 │
│              └────────────────────────────┘                 │
│                             │                                │
│        ┌────────────────────┼────────────────────┐         │
│        │                    │                    │         │
│        ▼                    ▼                    ▼         │
│  ┌──────────┐        ┌───────────┐       ┌──────────┐    │
│  │ Queue    │◀───────│ Worker    │──────▶│ Event    │    │
│  │ (IPC)    │ msgs   │ Process   │ poll  │ (cancel) │    │
│  └──────────┘        └───────────┘       └──────────┘    │
│        │                    │                              │
│        │                    └──────────────┐              │
│        │                                   ▼              │
│        │              ┌────────────────────────────────┐  │
│        │              │ Worker Process                 │  │
│        │              │                                │  │
│        │              │ 1. os.dup2(log_fd, stdout)    │  │
│        │              │ 2. import extract_slides      │  │
│        │              │ 3. on_progress adapter        │  │
│        │              │ 4. call engine                │  │
│        │              │ 5. return via queue           │  │
│        │              └────────────────────────────────┘  │
│        │                    │                              │
│        └────────────────────┘                              │
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │ Message Loop (drain until terminal)    │                │
│  │   STARTED    → log                     │                │
│  │   PROGRESS   → output_jsonl            │                │
│  │   SLIDE_SAVED→ manifest.add_asset()    │                │
│  │   DONE       → break                   │                │
│  │   ERROR      → raise                   │                │
│  └────────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Worker Process:
  stdout/stderr → log file (fd-level redirect)
  print() statements → captured, no pollution
  IPC → mp.Queue (structured messages)
```

---

## Code Changes Summary

### Modified Files

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `src/vidslide/worker.py` | ~130 | Real engine integration, adapters |
| `src/vidslide/extract.py` | ~50 | SLIDE_SAVED handling, manifest updates |
| `src/vidslide/probe.py` | ~6 | Pre-flight validation |

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_engine_integrity.py` | 34 | SHA256 verification |
| `tests/test_worker_integration.py` | 98 | Integration smoke tests |
| `docs/PHASE1_PROGRESS.md` | 203 | Progress tracker |

**Engine Modified:** 0 lines (byte-identical to baseline)

---

## Parameter Mapping

| CLI/Manifest | Engine Param | Mapping Logic |
|--------------|--------------|---------------|
| `threshold` | `threshold` | Direct pass-through |
| `enable_history` | `enable_history` | Direct (default: true) |
| `max_history` | `max_history` | Direct (default: 5) |
| `use_roi` | `use_roi` | Direct (default: true) |
| `fast_mode` | `fast_mode` | Direct (default: true) |
| `decoder: "auto"` | `use_gpu: True` | auto/gpu → True, cpu → False |
| `speed_mode: "fast"` | `speed_mode: "fast"` | Whitelist: eco/fast only |

---

## Message Protocol

### From Worker to Parent

```json
{"type": "STARTED"}

{"type": "PROGRESS", "progress": 42.5, "message": "Processing...", 
 "eta_seconds": 120.3, "elapsed_seconds": 45.2, "current_frame": 1234, 
 "slides_saved": 3}

{"type": "SLIDE_SAVED", "slide_index": 2, "source_frame": 1234, 
 "source_time_seconds": 41.13}

{"type": "DONE", "slides": 5, "message": "Extraction complete"}

{"type": "ERROR", "error": "...", "error_type": "ExtractionError"}
```

### Asset Naming Convention

Engine saves as: `slide_001.png`, `slide_002.png`, ..., `slide_NNN.png`

Manifest records:
```json
{
  "asset_id": "a_01JGXXX...",
  "filename": "slide_001.png",
  "provenance": {
    "source_frame": 1234,
    "source_time_seconds": 41.13,
    "extractor": "legacy-v041"
  }
}
```

---

## Testing Status

### ✅ Passing Tests

- **Engine integrity:** SHA256 matches baseline
- **Worker IPC:** Message protocol works
- **Cancel events:** mp.Event sticky behavior verified
- **fd-level redirect:** print() capture confirmed
- **Module imports:** No import errors

### ⚠️ Blocked Tests

**Blocker:** OpenCV not installed in environment

**Required for:**
- End-to-end extract test
- Golden baseline recording
- Regression test suite

**Installation:**
```bash
pip install opencv-python numpy
```

---

## Next Steps

### Immediate (Requires OpenCV)

1. **Install dependencies:**
   ```bash
   pip install opencv-python numpy
   ```

2. **Create synthetic test video:**
   - Use OpenCV to generate test frames
   - Scene A (5s) → fade → B (5s) → C (5s) → A (5s) → D (0.8s)
   - Expected: 3-4 slides depending on history

3. **End-to-end test:**
   ```bash
   ./vidslide.sh extract test_video.mp4
   ```

4. **Verify output:**
   - stdout is pure JSONL (no print() leakage)
   - manifest.json has correct assets
   - provenance is recorded
   - events.jsonl is complete

5. **Golden baseline:**
   - Record expected output
   - Create regression test
   - CI integration

### Future Enhancements (Phase 2+)

- Resume mechanism (start_frame, saved_offset)
- Ctrl-C signal handling (wire to cancel_event)
- Worker crash recovery
- Better error messages

---

## Verification Checklist

- [x] Engine file integrity (SHA256)
- [x] Worker process spawns
- [x] Message queue works
- [x] Cancel event works
- [x] fd-level redirect works
- [x] Module imports clean
- [ ] End-to-end extract (blocked: no OpenCV)
- [ ] stdout strictly JSONL (blocked: no OpenCV)
- [ ] Provenance correct (blocked: no OpenCV)
- [ ] Golden regression (blocked: no OpenCV)

---

## Commits

1. `eb2764e` - Initial Phase 1 infrastructure
2. `3204186` - Added legacy engine integration plan
3. `7f39365` - Integrate legacy v0.4.1 engine into worker process
4. `18a1975` - Add Phase 1 progress tracker
5. `1966ad4` - Add worker integration smoke tests

---

## Performance Notes

**Subagent Analysis:**
- Token usage: ~193k
- Time: ~20 minutes
- Value: Saved ~2 hours of debugging by discovering no Flask dependencies

**Integration Implementation:**
- Time: ~1.5 hours
- LOC: ~190 modified, 0 in engine
- Tests: All passing (5/5)

**Total Phase 1 (Steps 1-6):** ~3.5 hours vs estimated 4-5 hours

---

_Completed: 2025-01-02 21:30_
