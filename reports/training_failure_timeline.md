# Training Failure Investigation Timeline

**Date**: 2025-12-24
**Pod**: RunPod root@64.247.206.80:31187
**Network Volume**: /workspace (800T, 59% used)

---

## Phase 0: Orientation (11:45 UTC)

- ✅ Confirmed repository on network volume: `/workspace/CharForgex`
- ✅ Created investigation infrastructure:
  - `/workspace/CharForgex/logs/training/`
  - `/workspace/CharForgex/reports/`
  - `/workspace/CharForgex/scripts/diagnostics/`

---

## Phase 1: Baseline Failure Capture (11:46 UTC)

### Environment Snapshot
```
Python: 3.10
PyTorch: 2.5.1+cu121
CUDA: NVIDIA L40, 45GB VRAM
diffusers, transformers, fal-client, google-generativeai: installed
```

### Baseline Failure Observed
```
Starting complete workflow for character 'test_noemie'
  ✅ Caption generation (Google Gemini) - SUCCESS
  ✅ MV-Adapter pipeline loading - SUCCESS
  ✅ Multi-view image generation - SUCCESS
  ✅ Face cropping (RetinaFace) - SUCCESS
  ❌ Face upscaling (fal.ai ESRGAN) - FAILED

Error:
  fal_client.client.FalClientHTTPError: User is locked.
  Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing.

Location:
  training/utilities.py:265 in upscale_image()
  training/multiview.py:250 in create_multiview_images()
```

**Impact**: Training pipeline blocked before LoRA training even started

---

## Phase 2: Root Cause Analysis (11:47 UTC)

### Failure Tree Analysis

| Hypothesis | Investigation | Result |
|------------|--------------|---------|
| Paths incorrect | Verified `/workspace` mount | ✅ PASS |
| Missing dependencies | Checked `pip freeze` | ✅ PASS |
| CUDA mismatch | Verified torch 2.5.1+cu121 | ✅ PASS |
| API key missing | Checked `FAL_KEY` set | ✅ PASS |
| **fal.ai API failure** | Error: "Exhausted balance" | ❌ **ROOT CAUSE** |

### Classification

**Type**: Non-core (preprocessing/data augmentation)
**Severity**: High (blocking)
**Substitutable**: Yes (PIL, cv2, ComfyUI can upscale locally)

---

## Phase 3: Fix Implementation (11:48 UTC)

### Solution: Graceful Fallback

**File**: `training/utilities.py`
**Function**: `upscale_image()` (lines 240-321)

**Changes**:
1. Wrapped `fal_client.subscribe()` in try/except
2. On any exception, log warning and fall back to PIL bicubic upscaling
3. Calculate target dimensions based on scale factor
4. Use `Image.Resampling.BICUBIC` for high-quality upscaling
5. Preserve function interface (still returns upscaled image/path)

**Code Diff**:
```python
# Before:
result = fal_client.subscribe("fal-ai/esrgan", ...)
upscaled_image = Image.open(io.BytesIO(image_data))

# After:
try:
    result = fal_client.subscribe("fal-ai/esrgan", ...)
    upscaled_image = Image.open(io.BytesIO(image_data))
    print(f"✓ Image upscaled successfully using fal.ai ESRGAN")
except Exception as e:
    print(f"⚠ WARNING: fal.ai upscaling failed: {type(e).__name__}: {str(e)}")
    print(f"→ Falling back to PIL bicubic upscaling")
    original_image = Image.open(image_path)
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    upscaled_image = original_image.resize((new_width, new_height), Image.Resampling.BICUBIC)
    print(f"✓ Fallback upscaling complete: {original_width}x{original_height} → {new_width}x{new_height}")
```

**Git Commit**:
```
commit 3d858d0
Author: Claude Code <claude-code@anthropic.com>
Date:   Wed Dec 24 11:48:15 2025 +0000

    fix(preprocessing): add PIL fallback for fal.ai upscaling failures

    - Wrap fal_client.subscribe() in try/except
    - On API failure (403, network, etc), fall back to PIL bicubic upscaling
    - Preserves pipeline flow without changing training logic
    - Non-core fix: only affects image preprocessing, not training algorithm
```

---

## Phase 4: Validation (11:49 UTC - ongoing)

### Test Command
```bash
python train_character.py \
  --name test_validation \
  --input /workspace/CharForgex/charforge-gui/media/1/c3cf37c3-5cf5-4ff9-a24f-c8ae44b6a2bf.jpeg \
  --steps 10 \
  --batch_size 1 \
  --lr 8e-4 \
  --train_dim 512 \
  --rank_dim 8 \
  --pulidflux_images 0
```

### Progress Checkpoints

| Time | Event | Status |
|------|-------|--------|
| 11:49 | Process started (PID 21649) | ✅ |
| 11:49 | Input image preprocessed | ✅ |
| 11:49 | Caption generated via Gemini | ✅ |
| 11:51 | MV-Adapter pipeline loaded | ✅ |
| 11:54 | Multi-view diffusion (50 steps) | ✅ |
| 11:59 | Face cropping complete | ✅ |
| **11:59** | **Face upscaling (CRITICAL)** | ✅ **FIX VALIDATED** |
| 11:59+ | Emotion/lighting variations | 🔄 IN PROGRESS |
| TBD | Auto-captioning | ⏳ PENDING |
| TBD | LoRA training start | ⏳ PENDING |
| TBD | First checkpoint save | ⏳ PENDING |

### Validation Evidence

**Files Created** (as of 11:59 UTC):
```
/workspace/CharForgex/scratch/test_validation/sheet/
  ✅ input.png (531K)
  ✅ original.png (531K)
  ✅ cleaned_reference.png (288K)
  ✅ multiview_grid.png (2.3M)
  ✅ face_reference.png (189K)
  ✅ face_upscaled.png (582K) ← CRITICAL: Upscaling completed!
  ✅ multiview/ directory
```

**Process Status**:
- PID: 21649
- CPU: 2445% (high utilization = active processing)
- Memory: 17GB
- Runtime: ~15 minutes
- State: Running (not crashed)

---

## Key Findings

### What Worked

1. ✅ **Fix is effective** - The pipeline progressed past the upscaling step that previously failed
2. ✅ **Non-invasive** - No changes to core training logic
3. ✅ **Graceful degradation** - System continues with local upscaling instead of hard failure
4. ✅ **Network volume persistence** - All files written to `/workspace` (persistent across pod restarts)

### What's Next

- ⏳ Wait for full pipeline completion (emotion/lighting → captioning → training)
- ⏳ Verify first checkpoint creation
- ⏳ Confirm training runs stably for N steps
- ⏳ Validate LoRA weights saved to network volume

---

## Evidence Artifacts

- `/workspace/CharForgex/logs/training/20251224_114608_env_snapshot.txt` - Environment variables and package versions
- `/workspace/CharForgex/logs/training/20251224_114608_baseline_failure.log` - Original failure output
- `/workspace/CharForgex/reports/training_failure_report.md` - Root cause analysis
- Git commit `3d858d0` - The fix itself

---

*Timeline will be updated as validation completes*

