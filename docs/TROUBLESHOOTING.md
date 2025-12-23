# Troubleshooting Guide

[Back to README](../README.md)

This document provides expanded diagnostics for common issues, with concrete commands to inspect logs/outputs and verify paths.

---

## Quick Diagnosis Commands

```bash
# Check GPU status and memory
nvidia-smi

# Check environment variables are loaded
source .venv/bin/activate
python -c "import os; print('HF_TOKEN:', os.environ.get('HF_TOKEN', 'NOT SET')[:10] + '...')"

# Check if LoRA exists
ls -la ./scratch/CHARACTER_NAME/char/char.safetensors

# Check training timing
cat ./scratch/CHARACTER_NAME/timing.log

# Check captions
cat ./scratch/CHARACTER_NAME/sheet/*.txt | head -20

# Check for error in recent runs
tail -100 ~/.cache/huggingface/hub/*.log 2>/dev/null || echo "No HF logs"
```

---

## VRAM Issues

### Symptom: `CUDA out of memory` During Training

**Console output**:
```
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate X MiB
```

**Diagnosis**:
```bash
# Check current VRAM usage
nvidia-smi

# Check for zombie processes
ps aux | grep python | grep -v grep
```

**Causes and Fixes**:

| Cause | Fix |
|-------|-----|
| Other GPU processes running | Kill other processes: `pkill -f python` |
| VRAM < 48GB | Cannot run full pipeline; use inference-only with smaller batch |
| Previous run didn't clean up | Restart Python: `exit` then reactivate venv |
| Batch size too high | Reduce: `--batch_size 1` |

**Verify fix**:
```bash
nvidia-smi
# Should show minimal VRAM usage before starting
```

### Symptom: `CUDA out of memory` During Inference

**Diagnosis**:
```bash
# Check if FaceEnhance was enabled
# (requires significantly more VRAM)
```

**Fixes**:
1. Disable face enhancement: `--no_face_enhance`
2. Reduce batch size: `--batch_size 1`
3. Ensure GPU memory is clear before running

### Symptom: `CUDA out of memory` During Multiview Generation

This stage is the most memory-intensive.

**Fixes**:
1. Ensure no other GPU processes
2. Try with a lower resolution reference image
3. Restart Python environment completely

---

## API Key Errors

### Symptom: HuggingFace 401/403 Errors

**Console output**:
```
huggingface_hub.utils.HfHubHTTPError: 401 Client Error: Unauthorized
```

**Diagnosis**:
```bash
# Test token
python -c "
from huggingface_hub import HfApi
api = HfApi()
print(api.whoami())
"
```

**Causes and Fixes**:

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token invalid or expired | Regenerate at https://huggingface.co/settings/tokens |
| 403 Forbidden | No access to gated model | Accept license at https://huggingface.co/black-forest-labs/FLUX.1-dev |
| Token not found | HF_TOKEN not in .env | Add to .env file |

### Symptom: Google Gemini 401/403/429 Errors

**Console output**:
```
google.api_core.exceptions.Unauthenticated: 401
```
or
```
Resource exhausted: 429
```

**Diagnosis**:
```bash
# Check key format (should start with AIzaSy)
echo $GOOGLE_API_KEY | head -c 10
```

**Causes and Fixes**:

| Error | Cause | Fix |
|-------|-------|-----|
| 401 | Invalid API key | Regenerate at https://aistudio.google.com/app/apikey |
| 403 | API not enabled | Enable Gemini API in Google Cloud Console |
| 429 | Rate limit exceeded | Wait 60 seconds, or upgrade tier |

**Built-in retry**: The pipeline has retry logic for 429 errors. If persistent, slow down operations.

### Symptom: fal.ai Errors

**Console output**:
```
fal_client.exceptions.FalClientError: 402 Payment Required
```
or
```
fal_client.exceptions.FalClientError: 500/502/504
```

**Fixes**:

| Error | Cause | Fix |
|-------|-------|-----|
| 402 | Insufficient credits | Add credits at https://fal.ai/dashboard/billing |
| 500/502/504 | Service issues | Retry in 5 minutes; check https://status.fal.ai |
| Timeout | Large image or slow response | Pipeline has retry logic; wait |

### Symptom: CivitAI Download Failures

**Console output**:
```
Error downloading from CivitAI
```

**Fixes**:
1. Regenerate API key at https://civitai.com/user/account
2. Update CIVITAI_API_KEY in .env
3. Re-run `bash setup.sh`

---

## Training Failures

### Symptom: Training Completes But No LoRA File

**Diagnosis**:
```bash
# Check if LoRA directory exists
ls -la ./scratch/CHARACTER_NAME/char/

# Check config was created
cat ./scratch/CHARACTER_NAME/config.yaml

# Check for errors in ai-toolkit output
# (look for error messages in console output during training)
```

**Causes and Fixes**:

| Cause | Fix |
|-------|-----|
| ai-toolkit crashed | Check console output for errors; re-run |
| Wrong work_dir | Verify path; LoRA is at `./scratch/{name}/char/char.safetensors` |
| Disk full | Check `df -h`; free space |
| Permissions | Check `ls -la ./scratch/`; fix with `chmod -R u+rwX ./scratch/` |

### Symptom: Captioner Fails

**Diagnosis**:
```bash
# Check if captions were created
ls ./scratch/CHARACTER_NAME/sheet/*.txt

# Check image_info.json exists
cat ./scratch/CHARACTER_NAME/sheet/image_info.json
```

**Causes and Fixes**:

| Cause | Fix |
|-------|-----|
| GOOGLE_API_KEY invalid | Regenerate and update .env |
| Rate limited | Wait 60 seconds, retry |
| LoRACaptioner not installed | Re-run `bash setup.sh` |
| image_info.json missing | Check sheet generation completed |

### Symptom: Sheet Generation Fails

**Diagnosis**:
```bash
# Check what images were created
ls -la ./scratch/CHARACTER_NAME/sheet/

# Check timing log for failed stage
cat ./scratch/CHARACTER_NAME/timing.log
```

**Causes and Fixes**:

| Failed Stage | Cause | Fix |
|--------------|-------|-----|
| Multi-view | MV-Adapter error | Check HF_HOME has space; check models downloaded |
| Emotion/lighting | ComfyUI issue | Re-run setup; check custom nodes installed |
| Upscaling | fal.ai error | Check FAL_KEY valid and has credits |

---

## ComfyUI Workflow Issues

### Symptom: `ComfyUI workflow error` or Missing Nodes

**Diagnosis**:
```bash
# Check if ComfyUI exists
ls -la ./ComfyUI/

# Check custom nodes
ls ./ComfyUI/custom_nodes/
```

**Fixes**:
1. Re-run setup:
   ```bash
   bash setup.sh
   ```

2. Manual node install:
   ```bash
   cd ComfyUI
   python -m pip install comfy-cli
   comfy node install comfyui-essentials
   # ... install other missing nodes
   ```

### Symptom: Model Not Found in ComfyUI

**Console output**:
```
Model not found: photon.safetensors
```

**Diagnosis**:
```bash
# Check models directory
ls ./ComfyUI/models/checkpoints/
ls ./ComfyUI/models/loras/
```

**Fixes**:
1. Re-run setup to download models
2. Check `CIVITAI_API_KEY` is valid
3. Manually download from CivitAI and place in correct directory

---

## Output Issues

### Symptom: Outputs Not Found / Wrong Paths

**Diagnosis**:
```bash
# Find all outputs for a character
find ./scratch/CHARACTER_NAME -name "*.jpg" -o -name "*.png" | head -20

# Check output directory
ls -la ./scratch/CHARACTER_NAME/output/
```

**Common path mistakes**:

| Expected | Common Mistake |
|----------|----------------|
| `./scratch/name/char/char.safetensors` | Looking in `./char/` |
| `./scratch/name/output/*.jpg` | Looking in `./output/` |
| `./scratch/name/sheet/*.png` | Looking in `./sheet/` |

### Symptom: Safety Check Blocks All Outputs

**Console output**:
```
🔒 Replaced unsafe image with blank placeholder
```

**Diagnosis**:
```bash
# Check what was flagged
ls -la ./scratch/CHARACTER_NAME/output/
# Blank images are very small (~5KB) vs real images (~200KB+)
```

**Causes**:
1. Model generating NSFW unintentionally
2. Prompt containing implicit triggers
3. False positive from safety model

**Fixes**:
1. Check prompt for problematic words
2. Temporarily disable safety check to debug:
   ```bash
   python test_character.py ... --no_safety_check
   ```
3. If outputs are actually fine, re-run with safety enabled

**Warning**: Only disable safety check for debugging. Re-enable for production use.

---

## Identity Issues

### Symptom: Outputs Don't Look Like Reference

**Diagnosis**:
1. Check training images:
   ```bash
   open ./scratch/CHARACTER_NAME/sheet/
   # Visually inspect each image
   ```

2. Check LoRA is loading:
   ```bash
   python test_character.py ... 2>&1 | grep "LoRA loaded"
   ```

3. Test at high LoRA weight:
   ```bash
   python test_character.py ... --lora_weight 0.95
   ```

**See**: [Fidelity Playbook - Diagnosing Identity Drift](FIDELITY_PLAYBOOK.md#diagnosing-identity-drift)

### Symptom: Face Changes Between Images

**Diagnosis**:
```bash
# Generate multiple with same settings
python test_character.py ... --batch_size 4
# Compare all 4 outputs
```

**Causes and Fixes**:

| Cause | Fix |
|-------|-----|
| LoRA weight too low | Increase `--lora_weight` to 0.8+ |
| Conflicting prompt | Simplify prompt; remove style descriptors |
| Bad training data | Re-train with better reference |

---

## Environment Issues

### Symptom: Module Not Found

**Console output**:
```
ModuleNotFoundError: No module named 'xxx'
```

**Fixes**:
1. Ensure venv is activated:
   ```bash
   source .venv/bin/activate
   which python  # Should show .venv path
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r base_requirements.txt
   ```

### Symptom: CUDA Not Available

**Console output**:
```
torch.cuda.is_available() returns False
```

**Diagnosis**:
```bash
# Check NVIDIA driver
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

**Fixes**:
1. Install NVIDIA driver
2. Reinstall PyTorch with CUDA:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

---

## Log Locations

| Log | Location | Contents |
|-----|----------|----------|
| Stage timing | `./scratch/{name}/timing.log` | Duration of each stage |
| Training config | `./scratch/{name}/config.yaml` | Actual training parameters |
| Image metadata | `./scratch/{name}/sheet/image_info.json` | Image descriptions |
| HuggingFace cache | `$HF_HOME/` | Downloaded models |
| ComfyUI logs | Console output during workflow | Node execution |

---

## Getting More Help

If issues persist:

1. Capture full console output
2. Note which stage failed
3. Check all relevant log files
4. Verify environment variables
5. Check disk space and GPU memory

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md) | [Environment Setup](ENV_SETUP.md)
