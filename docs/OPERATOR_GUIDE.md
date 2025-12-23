# Operator Guide: Gold Path Workflow

[Back to README](../README.md)

This guide walks through the complete workflow from a single reference image to generated outputs. Follow exactly for reproducible results.

---

## Prerequisites Checklist

Before starting, verify:

- [ ] GPU with 48GB+ VRAM available (`nvidia-smi` shows expected GPU)
- [ ] `.env` file exists in repo root with all keys populated
- [ ] `setup.sh` has been run successfully (check for `.venv/` directory)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] Reference image ready (see selection criteria below)

---

## Stage 1: Reference Image Preparation

### Select Your Reference Image

The reference image is the single most important input. Requirements:

| Aspect | Requirement |
|--------|-------------|
| Format | JPG or PNG |
| Resolution | Minimum 512x512, optimal 1024x1024+ |
| Face visibility | Unobstructed, clearly visible |
| Lighting | Even, no harsh shadows |
| Expression | Neutral or slight smile |
| Background | Simple, non-distracting |

### Verify Image

```bash
# Check image dimensions
file /path/to/your/reference.jpg
# Should show dimensions >= 512x512
```

---

## Stage 2: Training

### Execute Training

```bash
source .venv/bin/activate

python train_character.py \
  --name "your_character_name" \
  --input "/absolute/path/to/reference.jpg"
```

**Expected runtime**: 30-45 minutes on L40S GPU

### What Happens During Training

The pipeline executes these stages (visible in console output):

1. **Preprocessing** (~30s)
   - Copies original to `scratch/{name}/sheet/original.png`
   - Crops to square, resizes to 1536px max
   - Generates initial caption via Google Gemini

2. **Multi-view Generation** (~5 min)
   - Uses MV-Adapter on SDXL to create 6 views
   - Views: front, 45° left, 90° left, back, 90° right, 45° right
   - Upscales via fal.ai ESRGAN

3. **Emotion/Lighting Generation** (~5 min)
   - Creates 4 lighting conditions (overcast, sunset, nightclub, desert)
   - Creates 4 emotion variations (neutral, closed eyes, wink, surprise)
   - Uses IC-Light and LivePortrait

4. **Captioning** (~2 min)
   - Runs LoRACaptioner with Google Gemini
   - Creates `.txt` file for each image in `sheet/`

5. **Dataset Preprocessing** (~30s)
   - Ensures all images are 1024x1024
   - Validates caption files exist

6. **LoRA Training** (~20-30 min)
   - Runs ai-toolkit with FLUX.1-dev
   - Default: 800 steps, rank 8, 512px training resolution

### Monitor Progress

Watch the console for:

```
Step 1: Generating character sheet for 'your_character_name'
[timing info for each substage]
Step 2: Captioning character sheet images
[captioner output]
Training LoRA for character 'your_character_name'
[training step progress]
```

### Verify Training Success

```bash
# Check LoRA exists
ls -la ./scratch/your_character_name/char/char.safetensors
# Should show file ~20-50MB

# Check timing log
cat ./scratch/your_character_name/timing.log
# Shows time for each stage
```

Expected output structure:

```
./scratch/your_character_name/
├── sheet/
│   ├── original.png          # Your input image
│   ├── input.png             # Preprocessed square version
│   ├── upscaled_multiview_*.png  # 6 multi-view images
│   ├── upscaled_lighting_*.png   # 4 lighting variations
│   ├── upscaled_emotions_*.png   # 2 emotion variations
│   ├── face_upscaled.png     # High-res face crop
│   ├── *.txt                 # Caption files
│   ├── image_info.json       # Image metadata
│   └── trash/                # Unused intermediate files
├── char/
│   └── char.safetensors      # THE TRAINED LORA
├── config.yaml               # Training config used
└── timing.log                # Stage timing
```

---

## Stage 3: Inference (Image Generation)

### Basic Inference

```bash
python test_character.py \
  --character_name "your_character_name" \
  --prompt "A professional headshot, studio lighting, neutral background"
```

**Expected runtime**: ~60s (models loaded) or ~120s (cold start)

### Inference Parameters

| Parameter | Default | Recommended Range | Notes |
|-----------|---------|-------------------|-------|
| `--lora_weight` | 0.73 | 0.65-0.85 | Higher = stronger identity, less flexibility |
| `--test_dim` | 1024 | 1024 | Native resolution; don't change |
| `--batch_size` | 4 | 1-8 | More = faster but more VRAM |
| `--num_inference_steps` | 30 | 25-40 | More = higher quality, slower |

### Full Example with All Options

```bash
python test_character.py \
  --character_name "your_character_name" \
  --prompt "A candid portrait at a coffee shop, warm natural lighting" \
  --lora_weight 0.75 \
  --test_dim 1024 \
  --batch_size 4 \
  --num_inference_steps 30 \
  --do_optimize_prompt \
  --safety_check
```

### Check Outputs

```bash
ls -la ./scratch/your_character_name/output/
# Shows generated images with timestamps
```

---

## Stage 4: Optional Face Enhancement

Face enhancement improves facial detail but requires >48GB VRAM.

```bash
python test_character.py \
  --character_name "your_character_name" \
  --prompt "Your prompt here" \
  --face_enhance
```

**Warning**: This uses the ComfyUI face enhancement workflow and significantly increases generation time (~30s per image).

---

## Stage 5: Iteration and Refinement

### If Identity Is Weak

1. Increase LoRA weight:
   ```bash
   python test_character.py ... --lora_weight 0.85
   ```

2. Simplify prompt (remove conflicting style descriptors)

3. Check if training images in `sheet/` look correct

### If Outputs Look Wrong

1. Verify reference image meets all criteria
2. Check `sheet/` images for obvious issues
3. Review captions in `.txt` files for pollution
4. Re-train if necessary

### Re-Training

To re-train with different settings:

```bash
# Remove old training artifacts (keep sheet if good)
rm -rf ./scratch/your_character_name/char/

# Re-run with new settings
python train_character.py \
  --name "your_character_name" \
  --input "/path/to/reference.jpg" \
  --steps 1200 \
  --rank_dim 16
```

---

## Quick Reference Commands

```bash
# Activate environment
source .venv/bin/activate

# Train new character
python train_character.py --name "NAME" --input "/path/to/image.jpg"

# Basic inference
python test_character.py --character_name "NAME" --prompt "Your prompt"

# Inference with face enhancement
python test_character.py --character_name "NAME" --prompt "Your prompt" --face_enhance

# Check GPU status
nvidia-smi

# Check timing log
cat ./scratch/NAME/timing.log

# List available characters
ls ./scratch/
```

---

## Troubleshooting Quick Links

- [VRAM issues](TROUBLESHOOTING.md#vram-issues)
- [API key errors](TROUBLESHOOTING.md#api-key-errors)
- [Training failures](TROUBLESHOOTING.md#training-failures)
- [Identity drift](FIDELITY_PLAYBOOK.md#diagnosing-identity-drift)

[Back to README](../README.md)
