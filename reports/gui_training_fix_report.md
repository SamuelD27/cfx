# GUI Training Fix Report

**Date:** 2025-12-26
**Issue:** Training works from CLI but fails immediately when launched from GUI
**Status:** RESOLVED

## Summary

GUI training sessions were failing within 10-15 seconds with `status='failed'` and `progress=0.0`. The root cause was ComfyUI's argparse hijacking the argument parser and calling `sys.exit(2)` when it saw unrecognized arguments from `train_character.py`.

## Root Cause Analysis

### The Problem Chain

1. **Backend triggers training**: `POST /api/training/characters/{id}/train` starts a subprocess:
   ```python
   cmd = [sys.executable, "train_character.py", "--name", "X", "--steps", "100", ...]
   ```

2. **train_character.py loads**: When imported, `training.generate_sheet` triggers a chain:
   ```
   training/generate_sheet.py
   └── training/workflows/emotion_lighting.py
       └── from main import load_extra_path_config  (ComfyUI's main.py)
           └── parse_args()  # Called at module load time!
   ```

3. **ComfyUI's argparse crashes**: ComfyUI's `main.py` calls `argparse.parse_args()` on import. When it sees `--name`, `--steps`, etc., it doesn't recognize them and calls `sys.exit(2)`.

### Why CLI Worked But GUI Didn't

When running directly via CLI, the script was being tested with simple arguments or just `--help`. The lazy import fix deferred ComfyUI imports until after our argparse ran, but the problem remained: **ComfyUI's argparse still saw our CLI arguments when it eventually imported**.

## The Fix

### 1. train_character.py (CRITICAL)

Added code to clear `sys.argv` after parsing our arguments, before any ComfyUI imports:

```python
args = parser.parse_args()

# CRITICAL: Clear sys.argv after parsing to prevent ComfyUI's argparse from seeing our args.
# ComfyUI's main.py calls parse_args() on import, which calls sys.exit(2) on unrecognized args.
# By clearing argv now, ComfyUI's argparse will see no args and won't exit.
sys.argv = [sys.argv[0]]

if not os.path.exists(args.input):
    ...
```

This ensures:
1. Our argparse runs first and parses all our arguments
2. We save the parsed values to `args`
3. We clear `sys.argv` so only the script name remains
4. When ComfyUI imports later and calls `parse_args()`, it sees no arguments to complain about

### 2. Backend Error Logging Enhancement

Added comprehensive error logging to `charforge-gui/backend/app/api/training.py`:

- **Request ID correlation**: Each training session gets a unique 8-character ID (e.g., `fb4a1f9c`)
- **Structured logging**: All log messages include the request ID prefix `[{request_id}]`
- **Log file creation**: Training logs saved to `scratch/{name}/training_{request_id}.log`
- **Full traceback logging**: Exceptions logged with complete stack traces

Example log output:
```
2025-12-26 10:04:59,375 - app.api.training - INFO - [fb4a1f9c] Starting training for session 4, character 'gui_test'
2025-12-26 10:04:59,382 - app.api.training - INFO - [fb4a1f9c] Log file: /app/scratch/gui_test/training_fb4a1f9c.log
2025-12-26 10:04:59,385 - app.api.training - INFO - [fb4a1f9c] Config: name=gui_test, input=/tmp/test.png, steps=100
2025-12-26 10:04:59,385 - app.api.training - INFO - [fb4a1f9c] Starting charforge.run_training()
```

## Files Modified

| File | Change |
|------|--------|
| `train_character.py` | Added `sys.argv = [sys.argv[0]]` after argparse to prevent ComfyUI exit |
| `charforge-gui/backend/app/api/training.py` | Added request_id correlation, log file creation, traceback logging |

## Verification

### Before Fix
- Training session created: `id=3, status="pending"`
- 10-15 seconds later: `status="failed", progress=0.0`
- Log shows ComfyUI argparse error and `sys.exit(2)`

### After Fix
- Training session created: `id=4, status="pending"`
- Immediately transitions to: `status="running"`
- Process continues executing character sheet generation, captioning, training
- No argparse errors in logs

## Testing Commands

```bash
# Create test character
curl -X POST "http://localhost:8000/api/training/characters" \
  -H "Content-Type: application/json" \
  -d '{"name": "test_char", "input_image_path": "/tmp/test.png"}'

# Start training
curl -X POST "http://localhost:8000/api/training/characters/{id}/train" \
  -H "Content-Type: application/json" \
  -d '{"character_id": {id}, "steps": 100, ...}'

# Check status
curl "http://localhost:8000/api/training/characters/{id}/training"
```

## Lessons Learned

1. **Import side effects are dangerous**: ComfyUI's `main.py` calls `parse_args()` at module load time, which is an anti-pattern that can break scripts that import it.

2. **Lazy imports aren't enough**: Deferring imports prevents the crash at parse time, but doesn't solve the fundamental issue of ComfyUI seeing our arguments later.

3. **Clear sys.argv when safe**: After parsing your own arguments, clearing or resetting `sys.argv` protects against misbehaving imports that call `parse_args()` globally.

4. **Request ID correlation is essential**: Without a unique ID per request, tracing issues across async/background tasks is nearly impossible.

## Future Recommendations

1. Consider filing an issue with ComfyUI about their `parse_args()` side effect
2. Add integration tests that start training via API to catch regressions
3. Consider using `parse_known_args()` in ComfyUI if forking is an option
