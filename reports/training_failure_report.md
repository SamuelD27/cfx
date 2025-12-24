# Training Failure - Root Cause Analysis

**Investigation Date**: 2025-12-24
**Pod**: RunPod ssh root@64.247.206.80 -p 31187
**Investigator**: Claude Code (Opus 4.5)

---

## Executive Summary

**Status**: ❌ IDENTIFIED - External API Dependency Failure
**Severity**: High (blocks entire training pipeline)
**Root Cause**: fal.ai API balance exhausted during preprocessing
**Location**: `training/utilities.py:265` (`upscale_image` function)
**Classification**: **Non-core** - Preprocessing/data augmentation failure

The training pipeline fails **BEFORE** reaching the actual LoRA training phase. The failure occurs during character sheet generation when attempting to upscale the face reference image using fal.ai's ESRGAN service.

---

## Timeline of Failure

1. ✅ **Character sheet generation initiated** - Input image loaded successfully
2. ✅ **Caption generation** - Google Gemini 2.5 Flash successfully described the image
3. ✅ **Multi-view generation** - MV-Adapter generated 6 views (0°-315°)
4. ✅ **Face cropping** - RetinaFace successfully extracted face crop
5. ❌ **Face upscaling** - fal.ai ESRGAN API returned 403 Forbidden
6. ⛔ **Pipeline halted** - Training never started

---

## Root Cause Evidence

### Error Stack Trace
```
File "/workspace/CharForgex/training/utilities.py", line 265, in upscale_image
    result = fal_client.subscribe(
File "/app/.venv/lib/python3.10/site-packages/fal_client/client.py", line 1572, in subscribe
    handle = self.submit(
...
fal_client.client.FalClientHTTPError: User is locked.
Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing.
```

### Call Chain
```
train_character.py:419 (main)
  ↓
train_character.py:293 (build_character)
  ↓
train_character.py:103 (build_charsheet)
  ↓
training/generate_sheet.py:192 (generate_char_sheet)
  ↓
training/multiview.py:250 (create_multiview_images)
  ↓
training/utilities.py:265 (upscale_image) ← FAILURE POINT
```

### Environment Context
- **API Key Status**: FAL_KEY is set but account balance is exhausted
- **Network Volume**: ✅ Confirmed on `/workspace` (800T total, 59% used)
- **Repository Location**: `/workspace/CharForgex`
- **Python Environment**: `.venv` activated successfully
- **CUDA**: Available, NVIDIA L40 with 45GB VRAM
- **PyTorch**: 2.5.1+cu121

---

## Analysis: Core vs Non-Core

### Why This Is NON-CORE

1. **Preprocessing Only**: The upscaling occurs during data augmentation/preparation, not during gradient descent or model training
2. **External Dependency**: Uses fal.ai commercial API, not a fundamental ML operation
3. **Substitutable**: The upscaling can be replaced with local alternatives (PIL, cv2, ComfyUI nodes) without changing training semantics
4. **No Algorithm Impact**: The actual LoRA training algorithm (ai-toolkit) is never reached
5. **Data Quality**: Upscaling is a quality enhancement, not a requirement for training convergence

### What Would Be CORE (Not Touched)

- ai-toolkit LoRA training logic
- FLUX.1-dev model loading/inference
- Gradient computation and backpropagation
- Loss functions and optimizers
- Learning rate schedules
- LoRA rank/dimension architecture

---

## Fix Strategy

### Approach: Graceful Fallback with Local Upscaling

**Rationale**: Add try/except around fal.ai API call with PIL-based fallback

**Implementation**:
1. Attempt fal.ai ESRGAN upscaling (preserve existing behavior)
2. On API failure (403, 429, timeout, etc.), log warning
3. Fall back to PIL bicubic upscaling to target size
4. Continue pipeline normally

**Why This Is Safe**:
- Preserves function interface (still returns upscaled image)
- Training data still gets prepared (just without ML upscaling)
- No changes to training algorithm, hyperparameters, or model architecture
- Fail-safe behavior instead of hard failure
- Can be toggled via environment variable if needed

### Alternative Considered (Rejected)

- **Top up fal.ai balance**: External action, not a code fix
- **Skip upscaling entirely**: Would require changing downstream pipeline expectations
- **Use ComfyUI upscaling**: More complex, requires workflow changes

---

## Files Requiring Changes

### 1. `training/utilities.py`
**Line 240-297**: `upscale_image()` function
**Change**: Wrap `fal_client.subscribe()` in try/except with PIL fallback
**Type**: Non-core (preprocessing utility)

### 2. `scripts/diagnostics/check_fal_api.py` (NEW)
**Purpose**: Pre-flight check for fal.ai API availability
**Type**: Non-core (diagnostic tool)

---

## Validation Criteria

Fix is considered successful when:

1. ✅ Training pipeline runs past character sheet generation
2. ✅ Face upscaling completes (via fal.ai OR fallback)
3. ✅ LoRA training starts and runs for at least 10 steps
4. ✅ First checkpoint is saved to network volume
5. ✅ No silent failures or degraded quality warnings

---

## Next Steps

1. Implement fallback logic in `training/utilities.py`
2. Add diagnostic script to check API availability pre-flight
3. Run full training pipeline end-to-end
4. Validate first checkpoint creation
5. Document the fallback behavior in CLAUDE.md

---

## Appendix: Evidence Files

- `logs/training/20251224_XXXXXX_baseline_failure.log` - Full training output
- `logs/training/20251224_XXXXXX_env_snapshot.txt` - Environment variables and package versions
- `/tmp/test_training.log` - Original failure log (copied to investigation logs)

