# CharForgex: Identity LoRA Training Pipeline

CharForgex is an automated pipeline for training character-specific FLUX.1-dev LoRA models from a single reference image. Given one high-quality photo, it generates a multi-view character sheet, auto-captions the images, and trains a LoRA optimized for identity preservation. The goal is photorealistic outputs where the generated person is indistinguishable from the reference.

---

## Hardware Requirements

| Resource | Minimum | Recommended | What Breaks If Under |
|----------|---------|-------------|----------------------|
| GPU VRAM | 48GB | 48GB+ | OOM during multiview generation or training; pipeline halts |
| System RAM | 60GB | 64GB+ | ComfyUI workflows crash; Python killed by OOM |
| Disk Space | 100GB | 150GB+ | Model downloads fail; cache fills up |
| GPU | NVIDIA A6000/L40S/A100 | L40S or better | Unsupported; AMD/Intel not tested |

**Critical**: This pipeline is designed for high-end NVIDIA GPUs. Consumer GPUs (RTX 3090, 4090) may work for inference but will likely OOM during training. FaceEnhance requires >48GB VRAM.

---

## External API Dependencies

This pipeline requires multiple external APIs. **All are billed/metered** - ensure you have credits.

| API | Required | Used For | Failure Mode |
|-----|----------|----------|--------------|
| **HuggingFace** | Yes | FLUX.1-dev model download | Blocks setup; training impossible |
| **Google Gemini** | Yes | Image captioning, prompt optimization | Captions fail; identity drift in trained LoRA |
| **fal.ai** | Yes | ESRGAN upscaling, PuLID-Flux images | Sheet generation fails; lower quality outputs |
| **CivitAI** | Yes (setup) | Checkpoint model downloads | Setup fails; manual download required |

### Required Environment Variables

Create `.env` in repo root:

```bash
# HuggingFace - REQUIRED
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_HOME=/path/to/huggingface/cache   # Where models are stored (100GB+)

# Google Gemini - REQUIRED
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxx

# fal.ai - REQUIRED
FAL_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# CivitAI - REQUIRED for setup
CIVITAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

See [docs/ENV_SETUP.md](docs/ENV_SETUP.md) for detailed setup and validation.

---

## Quickstart

### Setup (One-time)

```bash
# 1. Clone with submodules
git clone --recursive https://github.com/your-repo/CharForgex.git
cd CharForgex

# 2. Create .env with your API keys (see above)
cp .env.example .env
# Edit .env with real values

# 3. Accept FLUX.1-dev license at HuggingFace
# https://huggingface.co/black-forest-labs/FLUX.1-dev

# 4. Run setup (downloads ~50GB of models)
bash setup.sh

# 5. Activate environment
source .venv/bin/activate
```

### Training (30-40 min on L40S)

```bash
python train_character.py \
  --name "person_name" \
  --input "/path/to/reference.jpg"
```

Output: `./scratch/person_name/char/char.safetensors`

### Inference

```bash
python test_character.py \
  --character_name "person_name" \
  --prompt "A professional headshot in a modern office"
```

Output: `./scratch/person_name/output/*.jpg`

See [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) for the complete workflow.

---

## Fidelity-First Operating Principles

The #1 goal is **identity fidelity**: generated images should be indistinguishable from photos of the real person.

### Reference Image Selection

Your reference image is the foundation. Bad input = bad LoRA.

| Criterion | Optimal | Acceptable | Avoid |
|-----------|---------|------------|-------|
| Lighting | Even, diffused, natural | Slightly directional | Harsh shadows, backlit, mixed color temps |
| Angle | Frontal, slight 3/4 | Clear profile | Extreme angles, looking away |
| Expression | Neutral, slight smile | Natural expression | Extreme expressions, eyes closed |
| Resolution | 1024px+ per side | 512px+ | Under 512px |
| Cropping | Head + shoulders visible | Face clearly visible | Cropped face, distant full-body |
| Occlusions | None | Minimal jewelry | Sunglasses, hats, masks, hands on face |
| Background | Clean, simple | Non-distracting | Busy, patterned, other faces |

### How the Pipeline Expands Data

From your single image, the pipeline generates:

| Stage | Images | Purpose | Fidelity Contribution |
|-------|--------|---------|----------------------|
| Multi-view | 6 | Front, sides, back views | **High** - teaches 3D face structure |
| Lighting | 4 | Overcast, sunset, nightclub, desert | **Medium** - prevents lighting overfitting |
| Emotions | 2 | Smiling, surprised | **Medium** - teaches expression range |
| PuLID-Flux | 0-N | Synthetic variations | **Variable** - can help or hurt |

**Warning**: PuLID-Flux images (`--pulidflux_images N`) can introduce identity drift if N is too high. Start with 0 or 3-5 max.

### Captioning and Identity

The auto-captioner (Google Gemini) creates `.txt` files describing each image. These captions directly affect what the LoRA learns.

**Key**: Captions should NOT include the person's name or identifying info. The LoRA learns the visual pattern, not the words. Adding names causes the model to associate random text patterns with the face.

### Inference for Maximum Fidelity

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| `--lora_weight` | 0.65-0.85 | Below 0.6 loses identity; above 0.9 loses flexibility |
| `--test_dim` | 1024 | Native resolution; higher adds no benefit |
| `--do_optimize_prompt` | enabled (default) | Uses LoRACaptioner to enhance prompt |
| `--num_inference_steps` | 28-35 | Lower = faster but may lose detail |

See [docs/FIDELITY_PLAYBOOK.md](docs/FIDELITY_PLAYBOOK.md) for deep guidance.

---

## Troubleshooting Matrix

| Symptom | Likely Cause | Fastest Fix |
|---------|--------------|-------------|
| `CUDA out of memory` during training | VRAM < 48GB or other GPU processes | Kill other GPU tasks; reduce batch_size to 1 |
| `CUDA out of memory` during inference | FaceEnhance enabled with insufficient VRAM | Use `--no_face_enhance` |
| Training completes but LoRA not found | Wrong `work_dir` or training failed silently | Check `./scratch/{name}/char/char.safetensors` exists |
| Captioner fails with 401/403 | Invalid or expired `GOOGLE_API_KEY` | Regenerate key at Google AI Studio |
| fal.ai timeout/500 errors | fal.ai service issues or rate limit | Retry in 5 min; check fal.ai status page |
| Setup fails downloading models | `CIVITAI_API_KEY` invalid | Get new key from civitai.com/user/account |
| `ComfyUI workflow error` | Missing custom nodes or models | Re-run `bash setup.sh` |
| Safety check blocks all outputs | Model generating NSFW unintentionally | Check prompt for implicit triggers; use `--no_safety_check` to debug |
| Identity drift in outputs | LoRA weight too low or prompt conflicts | Increase `--lora_weight` to 0.8+; simplify prompt |
| Outputs look nothing like reference | Bad reference image or caption pollution | Review ref image against criteria; re-train |

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for expanded diagnostics.

---

## File/Folder Map

```
CharForgex/
├── train_character.py      # Main training entrypoint
├── test_character.py       # Main inference entrypoint
├── setup.sh                # One-time setup script
├── install.py              # Installation logic
├── helpers.py              # Subprocess and LoRA utilities
├── .env                    # Your API keys (create from .env.example)
│
├── scratch/                # All character outputs
│   └── {character_name}/
│       ├── sheet/          # Generated training images
│       │   ├── original.png
│       │   ├── input.png
│       │   ├── upscaled_multiview_*.png
│       │   ├── upscaled_lighting_*.png
│       │   ├── upscaled_emotions_*.png
│       │   ├── face_upscaled.png
│       │   ├── *.txt       # Caption files
│       │   └── image_info.json
│       ├── char/           # Trained LoRA
│       │   └── char.safetensors
│       ├── output/         # Inference outputs
│       ├── config.yaml     # Training config used
│       └── timing.log      # Stage timing data
│
├── training/               # Training pipeline modules
├── inference/              # Inference and safety modules
├── scripts/                # Shell scripts and configs
├── charforge-gui/          # Optional web GUI
└── docs/                   # Documentation
```

---

## Known Limitations

- **Runtime**: Full training pipeline takes 30-45 minutes on L40S. Inference batch of 4 takes ~60s (models loaded) or ~120s (cold start).
- **Determinism**: Outputs are stochastic. Same prompt + seed does not guarantee identical output across runs due to model loading variations.
- **FaceEnhance**: Requires >48GB VRAM and adds ~30s per image. May alter skin texture.
- **PuLID-Flux**: Synthetic images can drift from identity. Test with 0 first, add sparingly.
- **Safety Checker**: May false-positive on non-NSFW content. Use `--no_safety_check` to debug, then re-enable.
- **Consumer GPUs**: RTX 3090/4090 may work for inference only; training will OOM.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) | Step-by-step workflow from image to inference |
| [docs/FIDELITY_PLAYBOOK.md](docs/FIDELITY_PLAYBOOK.md) | Deep guidance on maximizing identity accuracy |
| [docs/ENV_SETUP.md](docs/ENV_SETUP.md) | Environment variables, API key setup, validation |
| [docs/PIPELINE_OVERVIEW.md](docs/PIPELINE_OVERVIEW.md) | Architecture diagram and code flow |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Expanded error diagnosis and fixes |
| [docs/GUI_LOCAL.md](docs/GUI_LOCAL.md) | Running the optional web GUI locally |
| [docs/DOCKER.md](docs/DOCKER.md) | Docker container usage |

---

## Advanced Usage

### Custom Training Parameters

Edit `scripts/character_lora.yaml` or pass CLI flags:

```bash
python train_character.py \
  --name "person" \
  --input "ref.jpg" \
  --steps 1200 \           # More training (default: 800)
  --rank_dim 16 \          # Higher LoRA rank (default: 8)
  --train_dim 768 \        # Higher res training images (default: 512)
  --pulidflux_images 5     # Add synthetic images (default: 0)
```

### Serving LoRA Weights

```bash
python scripts/serve_lora.py --character_name "person"
# Serves LoRA via FastAPI for remote inference
```

### Manual ComfyUI

```bash
python scripts/run_comfy.py
# Launches ComfyUI server for manual workflow editing
```

### Symlink LoRAs to ComfyUI

```bash
bash scripts/symlink_loras.sh
# Links all scratch/*/char/*.safetensors to ComfyUI/models/loras/
```
