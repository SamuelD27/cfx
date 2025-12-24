# CharForgex - Claude Code Project Guide

## What This Repo Is

CharForgex (CharForge) is an **AI-powered character LoRA creation pipeline** that automates the process of training custom LoRA models on FLUX.1-dev. Given a single reference image, it generates a multi-view character sheet, auto-captions images using Google Gemini, and trains a LoRA using ai-toolkit. The pipeline includes:

1. **Character sheet generation** - Multi-view images, lighting variations, facial expressions via ComfyUI workflows
2. **Auto-captioning** - Using LoRACaptioner with Google Gemini 2.5 Flash
3. **LoRA training** - Using ostris/ai-toolkit on FLUX.1-dev
4. **Inference** - Diffusers-based image generation with the trained LoRA
5. **Optional GUI** - Vue 3 + FastAPI web interface for managing the pipeline

## What This Repo Is NOT

- Not a general-purpose image generation tool (focused specifically on character LoRAs)
- Not designed for CPU-only systems (requires GPU with 48GB+ VRAM for full pipeline)
- Not a hosted service (meant to run locally or on your own GPU server)
- Not production-ready for public deployment without additional security hardening

---

## High-Level Architecture

```
CharForgex/
├── train_character.py        # Main training CLI entrypoint
├── test_character.py         # Main inference CLI entrypoint
├── install.py                # Installation and setup logic
├── helpers.py                # Utility functions (subprocess, LoRA finding, prompt optimization)
├── training/                 # Training pipeline modules
│   ├── generate_sheet.py     # Orchestrates character sheet generation
│   ├── multiview.py          # MV-Adapter multi-view generation
│   ├── emotion_lighting.py   # Emotion/lighting variations
│   ├── pulid_flux_images.py  # PuLID-Flux synthetic image generation (fal.ai)
│   ├── utilities.py          # Captioning, upscaling, face cropping
│   └── workflows/            # ComfyUI Python workflows (emotion_lighting, upscale_grid)
├── inference/                # Inference modules
│   ├── safety.py             # NSFW detection using Falconsai model
│   ├── postprocess.py        # FaceEnhancer wrapper
│   └── workflows/            # ComfyUI face enhancement workflow
├── scripts/                  # Shell/config scripts
│   ├── character_lora.yaml   # Template for LoRA training config
│   ├── run_ai_toolkit.sh     # Runs ai-toolkit in isolated venv
│   ├── run_captioner.sh      # Runs LoRACaptioner in isolated venv
│   └── serve_lora.py         # FastAPI server for serving LoRA weights
├── charforge-gui/            # Optional web GUI
│   ├── backend/              # FastAPI + SQLAlchemy backend
│   └── frontend/             # Vue 3 + TypeScript + TailwindCSS
├── ai_toolkit/               # Git submodule: ostris/ai-toolkit
├── LoRACaptioner/            # Git submodule: RishiDesai/LoRACaptioner
├── MV_Adapter/               # Git submodule: RishiDesai/MV-Adapter
├── ComfyUI_AutoCropFaces/    # Git submodule: face cropping utilities
├── ComfyUI/                  # Git submodule (installed via setup)
└── examples/                 # Sample input images
```

### Data Flow

```
Input Image
    │
    ▼
[generate_sheet.py] ──────────────────────────────────────────────┐
    │                                                              │
    ├── rectangle_to_square + resize                               │
    ├── generate_caption (Gemini 2.5 Flash)                        │
    ├── create_multiview_images (MV-Adapter + SDXL)                │
    ├── apply_upscale_grid_image (fal.ai ESRGAN + ComfyUI PuLID)   │
    ├── generate_emotion_lighting (IC-Light + LivePortrait)        │
    └── (optional) generate_synthetic_images (PuLID-Flux via fal)  │
                                                                   │
    ▼                                                              │
[./scratch/{name}/sheet/] ◄────────────────────────────────────────┘
    │   ├── *.png images
    │   └── *.txt captions (via LoRACaptioner)
    │
    ▼
[train_lora via ai-toolkit]
    │
    ▼
[./scratch/{name}/char/char.safetensors]
    │
    ▼
[test_character.py] ──► inference via diffusers ──► output images
```

---

## Golden Paths (Copy-Paste Commands)

### First-Time Setup (Mac with GPU or Remote GPU Server)

```bash
# 1. Clone the repo
git clone --recursive https://github.com/your-username/CharForgex.git
cd CharForgex

# 2. Create .env file with your API keys
cat > .env << 'EOF'
HF_TOKEN=your_huggingface_token
HF_HOME=/path/to/huggingface/cache
CIVITAI_API_KEY=your_civitai_key
GOOGLE_API_KEY=your_google_genai_key
FAL_KEY=your_fal_ai_key
EOF

# 3. Run setup (requires CUDA GPU)
bash setup.sh

# 4. Activate the environment
source .venv/bin/activate
```

### Train a Character LoRA

```bash
# Basic training
python train_character.py --name "my_character" --input "path/to/reference.png"

# With custom parameters
python train_character.py \
  --name "my_character" \
  --input "path/to/reference.png" \
  --steps 800 \
  --batch_size 1 \
  --lr 8e-4 \
  --train_dim 512 \
  --rank_dim 8 \
  --pulidflux_images 5
```

### Generate Images with Trained LoRA

```bash
# Basic inference
python test_character.py \
  --character_name "my_character" \
  --prompt "A detailed portrait of this person in a garden"

# With all options
python test_character.py \
  --character_name "my_character" \
  --prompt "Your detailed prompt here" \
  --lora_weight 0.73 \
  --test_dim 1024 \
  --batch_size 4 \
  --num_inference_steps 30 \
  --do_optimize_prompt \
  --safety_check
```

### Run the Web GUI

```bash
cd charforge-gui
./start-dev.sh
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
```

### Run Tests / Verify Syntax

```bash
# Syntax check main files
python3 -c "import ast; ast.parse(open('train_character.py').read())"
python3 -c "import ast; ast.parse(open('test_character.py').read())"

# Check helpers can import
python3 -c "import helpers; print('OK')"
```

---

## Repository Map

| Folder/File | Description |
|-------------|-------------|
| `train_character.py` | Main CLI for training - orchestrates sheet generation, captioning, LoRA training |
| `test_character.py` | Main CLI for inference - loads LoRA and generates images |
| `install.py` | Installation script - sets up ComfyUI, custom nodes, downloads models |
| `setup.sh` | Shell wrapper for installation |
| `helpers.py` | Utility functions for subprocess execution, LoRA finding, prompt optimization |
| `training/` | All training-related modules |
| `training/generate_sheet.py` | Orchestrates the character sheet generation pipeline |
| `training/multiview.py` | Multi-view image generation using MV-Adapter |
| `training/emotion_lighting.py` | Emotion and lighting variation generation |
| `training/pulid_flux_images.py` | PuLID-Flux synthetic image generation via fal.ai |
| `training/utilities.py` | Image utilities - captioning, upscaling, face cropping |
| `training/workflows/` | ComfyUI Python workflows converted from node graphs |
| `inference/` | Inference-related modules |
| `inference/safety.py` | NSFW detection using Falconsai/nsfw_image_detection |
| `inference/postprocess.py` | Face enhancement wrapper class |
| `scripts/` | Shell scripts and config templates |
| `scripts/character_lora.yaml` | Template YAML config for ai-toolkit training |
| `charforge-gui/` | Optional Vue 3 + FastAPI web interface |
| `ai_toolkit/` | Git submodule - ostris/ai-toolkit for LoRA training |
| `LoRACaptioner/` | Git submodule - auto-captioning with Gemini |
| `MV_Adapter/` | Git submodule - multi-view image generation |
| `ComfyUI_AutoCropFaces/` | Git submodule - face cropping with RetinaFace |
| `examples/` | Sample input images for testing |

---

## Configuration Guide

### Required Environment Variables

Create a `.env` file in the root directory:

```bash
# Hugging Face (REQUIRED)
HF_TOKEN=hf_xxxxxxxxxxxx          # For downloading FLUX.1-dev and other models
HF_HOME=/path/to/cache            # Where to store downloaded models

# CivitAI (REQUIRED for full setup)
CIVITAI_API_KEY=xxxxxxxxxxxx      # For downloading checkpoint models

# Google AI (REQUIRED for captioning)
GOOGLE_API_KEY=AIzaSyxxxxxxxxx    # For Gemini 2.5 Flash captioning

# fal.ai (REQUIRED for upscaling and PuLID-Flux)
FAL_KEY=xxxxxxxx                  # For ESRGAN upscaling and PuLID-Flux generation
```

### Key Config Files

| File | Purpose |
|------|---------|
| `scripts/character_lora.yaml` | Template for LoRA training - placeholders replaced at runtime |
| `charforge-gui/.env.example` | GUI configuration template |
| `ai_toolkit/config/examples/*.yaml` | Example configs for different model types |

### Training Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--steps` | 800 | Training steps (500-4000 recommended) |
| `--batch_size` | 1 | Training batch size |
| `--lr` | 8e-4 | Learning rate |
| `--train_dim` | 512 | Training image resolution |
| `--rank_dim` | 8 | LoRA rank dimension |
| `--pulidflux_images` | 0 | Number of PuLID-Flux synthetic images |

---

## Operational Knowledge

### Where Logs Are

- Training timing: `./scratch/{character_name}/timing.log`
- ComfyUI logs: Console output during execution
- GUI backend logs: Console output from uvicorn

### Where Outputs/Artifacts Are Written

```
./scratch/{character_name}/
├── sheet/                    # Generated character sheet images + captions
│   ├── original.png          # Original input image
│   ├── input.png             # Preprocessed (squared, resized)
│   ├── upscaled_multiview_*.png
│   ├── upscaled_lighting_*.png
│   ├── upscaled_emotions_*.png
│   ├── face_upscaled.png
│   ├── *.txt                 # Caption files
│   ├── image_info.json       # Image metadata
│   └── trash/                # Unused intermediate images
├── char/                     # Trained LoRA model
│   └── char.safetensors      # Final LoRA weights
├── output/                   # Generated inference images
├── config.yaml               # Customized training config
└── timing.log                # Timing data for each step
```

### Debugging Tips / Common Pitfalls

1. **CUDA OOM**: The full pipeline requires 48GB+ VRAM. Use smaller batch_size or resolution.
2. **Missing models**: Run `python install.py` again to re-download missing models.
3. **API rate limits**: Google Gemini has rate limits; the code includes retry logic.
4. **Submodule issues**: Run `git submodule update --init --recursive` if submodules are empty.
5. **fal.ai failures**: Check FAL_KEY is valid and has credits; the code includes retry logic.
6. **ComfyUI node errors**: Ensure all custom nodes are installed via `comfy node install`.

---

## Development Conventions

### Code Style

- Python: Standard Python 3.10+ conventions, dataclasses for configs
- Type hints: Used throughout for function signatures
- Imports: Grouped by standard library, third-party, local
- GUI Backend: FastAPI with Pydantic models
- GUI Frontend: Vue 3 Composition API with TypeScript

### Testing

- No formal test suite currently
- Syntax validation: `python -c "import ast; ast.parse(open('file.py').read())"`
- Manual testing recommended before commits

### Branching/PR Guidelines

- Main branch: `main`
- Feature branches: `feature/{description}`
- Bug fixes: `fix/{description}`

---

## Known Issues / TODOs

### High Priority

1. **No formal test suite** - Only syntax validation available; unit tests should be added
2. **README is incomplete** - Some markdown formatting issues in the existing README
3. **GPU requirement not clearly documented** - Minimum requirements (48GB VRAM) need emphasis

### Medium Priority

1. **Error handling** - Some error paths print warnings but continue silently
2. **Config validation** - Limited validation of training config parameters
3. **Cleanup on failure** - Intermediate files may be left behind if process fails

### Low Priority

1. **Duplicate scratch/ entries in .gitignore**
2. **Some hardcoded model paths** in workflow files
3. **Limited progress reporting** during training

---

## How to Ask Claude for Help in THIS Repo

### Example Prompts

1. **"Trace how the character sheet generation works from input image to final images"**
   - Start at `train_character.py:build_charsheet()`, then follow to `training/generate_sheet.py`

2. **"How do I add a new lighting condition to the emotion_lighting workflow?"**
   - Look at `training/workflows/emotion_lighting.py`, find the `string_literal` definitions

3. **"What happens if the face detection fails?"**
   - Check `training/utilities.py:crop_face()` - it returns False and logs a warning

4. **"How do I change the LoRA training hyperparameters?"**
   - Modify `scripts/character_lora.yaml` or pass CLI args to `train_character.py`

5. **"How do I run the GUI in production mode?"**
   - Check `charforge-gui/DEPLOYMENT_GUIDE.md` and use `./deploy.sh production`

6. **"What external APIs does this project use?"**
   - Google Gemini (captioning/prompts), fal.ai (upscaling/PuLID-Flux), HuggingFace (models)

7. **"How do I add a new post-processing step to inference?"**
   - Look at `test_character.py:LoRAImageGen.generate()` for the flow

8. **"What models are downloaded during setup?"**
   - See `install.py:download_huggingface_models()` and `download_external_models()`

9. **"How do I debug a failing ComfyUI workflow?"**
   - Run `python scripts/run_comfy.py` to start ComfyUI server, then load workflow manually

10. **"How do I add support for a new base model?"**
    - Check `ai_toolkit/config/examples/` for config templates of different models

---

## Persistent Volume Workflow (RunPod)

### Overview

When working with RunPod pods, use a **Network Volume** to persist data across pod restarts/terminations. This prevents re-downloading ~50GB of models each time.

### Setup Network Volume

1. **Create Network Volume** in RunPod dashboard (recommended: 100GB minimum)
2. **Attach to Pod** at mount point `/workspace` or `/runpod-volume`
3. **First boot**: Models download to volume, setup marker created
4. **Subsequent boots**: Marker detected, setup skipped

### Directory Structure on Volume

```
/runpod-volume/                    # Or /workspace
├── CharForgex/                    # Clone repo here
│   ├── .setup_complete            # Marker file (created after first setup)
│   ├── .venv/                     # Python virtual environment
│   ├── scratch/                   # Character working directories
│   ├── ComfyUI/                   # ComfyUI installation
│   └── ...
├── huggingface/                   # HF_HOME cache
│   └── hub/                       # Downloaded models (~30GB)
└── models/                        # Additional model storage
```

### Environment Variables for Volume

```bash
# Add to .env for persistent volume
HF_HOME=/runpod-volume/huggingface
SCRATCH_DIR=/runpod-volume/CharForgex/scratch
```

### Syncing Code Changes

When updating code on the volume:
```bash
cd /runpod-volume/CharForgex
git pull origin main
# No need to re-run setup.sh unless dependencies changed
```

---

## Core Pipeline Deep Dive

### CRITICAL: Do Not Modify These Components

The following are the **core ML components** that should NOT be modified without deep understanding:

| Component | Location | Purpose | Why Not Touch |
|-----------|----------|---------|---------------|
| ai-toolkit training | `ai_toolkit/` submodule | LoRA training on FLUX.1-dev | Proven training logic |
| MV-Adapter | `MV_Adapter/` submodule | Multi-view generation | Complex diffusion pipeline |
| LoRACaptioner | `LoRACaptioner/` submodule | Auto-captioning with Gemini | Prompt engineering tuned |
| ComfyUI workflows | `training/workflows/` | Image processing graphs | Node connections fragile |

### Training Pipeline: Step-by-Step Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ train_character.py --name "X" --input "image.png"                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: build_charsheet() → training/generate_sheet.py                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1.1 rectangle_to_square()     - Pad image to square aspect ratio            │
│ 1.2 resize_image()            - Resize to train_dim (default 512)           │
│ 1.3 generate_caption()        - Google Gemini describes the person          │
│ 1.4 create_multiview_images() - MV-Adapter generates 6 views (0°-315°)      │
│ 1.5 apply_upscale_grid()      - fal.ai ESRGAN 4x upscale                    │
│ 1.6 emotion_lighting()        - IC-Light + LivePortrait variations          │
│ 1.7 crop_face()               - RetinaFace extracts face crop               │
│ 1.8 (optional) pulid_flux()   - Generate synthetic training images          │
│                                                                             │
│ OUTPUT: ./scratch/{name}/sheet/*.png + *.txt captions                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: run_captioner() → scripts/run_captioner.sh                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Activates LoRACaptioner venv                                              │
│ - Runs Gemini 2.5 Flash on each image                                       │
│ - Creates {image}.txt caption files with trigger word                       │
│                                                                             │
│ OUTPUT: ./scratch/{name}/sheet/*.txt (one per image)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: train_lora() → scripts/run_ai_toolkit.sh                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Generates config.yaml from scripts/character_lora.yaml template           │
│ - Activates ai-toolkit venv                                                 │
│ - Runs: python run.py config.yaml                                           │
│ - Trains LoRA on FLUX.1-dev with specified parameters                       │
│                                                                             │
│ PARAMETERS:                                                                 │
│   steps: 800 (default)      - Training iterations                           │
│   batch_size: 1             - Images per batch                              │
│   learning_rate: 8e-4       - AdamW optimizer LR                            │
│   rank_dim: 8               - LoRA rank (higher = more capacity)            │
│   train_dim: 512            - Image resolution during training              │
│                                                                             │
│ OUTPUT: ./scratch/{name}/char/char.safetensors                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Inference Pipeline: Step-by-Step Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ test_character.py --character_name "X" --prompt "..."                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Models                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Load FLUX.1-dev pipeline from HuggingFace                                 │
│ - Load trained LoRA: ./scratch/{name}/char/char.safetensors                 │
│ - Apply LoRA with specified weight (default 0.73)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Prompt Optimization (optional: --do_optimize_prompt)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Send prompt to Google Gemini                                              │
│ - Gemini enhances prompt with artistic details                              │
│ - Preserves original intent while adding quality keywords                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Image Generation                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Run FLUX.1-dev diffusion with LoRA applied                                │
│ - Parameters: test_dim, num_inference_steps, guidance_scale                 │
│ - Generate batch_size images                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Safety Check (optional: --safety_check)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Run Falconsai/nsfw_image_detection on output                              │
│ - Flag or filter unsafe images                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Post-processing (optional)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Face enhancement via ComfyUI workflow                                     │
│ - Upscaling if requested                                                    │
│                                                                             │
│ OUTPUT: ./scratch/{name}/output/*.png                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### GUI ↔ Backend ↔ CLI Mapping

| GUI Action | API Endpoint | CLI Equivalent |
|------------|--------------|----------------|
| Create Character | `POST /api/training/characters` | N/A (done in train_character.py) |
| Upload Image | `POST /api/media/upload` | `--input path/to/image.png` |
| Start Training | `POST /api/training/characters/{id}/train` | `python train_character.py --name X` |
| View Training Status | `GET /api/training/characters/{id}/training` | Check `scratch/{name}/timing.log` |
| Generate Image | `POST /api/inference/generate` | `python test_character.py --character_name X` |
| View Generated Images | `GET /api/inference/jobs/{id}` | Check `scratch/{name}/output/` |
| Configure Settings | `POST /api/settings/environment` | Edit `.env` file |

---

## Comprehensive Logging System

### Enable Full Debug Logging

To trace exactly what happens during any operation, enable debug logging:

#### 1. Backend API Logging

Edit `charforge-gui/backend/app/main.py` or set environment:
```bash
export CHARFORGE_LOG_LEVEL=DEBUG
```

All API requests/responses logged to console with:
- Timestamp
- Endpoint called
- Request body (sanitized)
- Response status
- Execution time

#### 2. Training Pipeline Logging

Training automatically logs to `./scratch/{character_name}/timing.log`:
```
[2025-12-24 10:00:00] START: build_charsheet
[2025-12-24 10:00:05] STEP: rectangle_to_square (5.2s)
[2025-12-24 10:00:10] STEP: generate_caption (4.8s)
[2025-12-24 10:02:30] STEP: create_multiview_images (140.0s)
...
[2025-12-24 10:45:00] END: train_lora (total: 45m 0s)
```

#### 3. ComfyUI Workflow Logging

ComfyUI logs to `/tmp/comfyui.log` in Docker, or console when run directly:
```bash
# View ComfyUI logs in real-time
tail -f /tmp/comfyui.log
```

#### 4. Frontend Action Logging

Enable browser console logging in `frontend/src/services/api.ts`:
```typescript
// Already includes request/response logging
// Check browser DevTools → Console for:
// - API calls made
// - Response data
// - Errors with stack traces
```

### Log Locations Summary

| Component | Log File | What's Logged |
|-----------|----------|---------------|
| Backend API | `/tmp/backend.log` or console | All HTTP requests, DB queries |
| Frontend | Browser Console | API calls, Vue component lifecycle |
| Training Pipeline | `scratch/{name}/timing.log` | Step durations, success/failure |
| ComfyUI | `/tmp/comfyui.log` | Workflow execution, node outputs |
| Setup Script | `/tmp/setup.log` | Model downloads, dependency installs |
| ai-toolkit | Console during training | Loss values, checkpoints saved |

### Real-Time Log Monitoring

```bash
# Monitor all logs simultaneously (in tmux or multiple terminals)
tail -f /tmp/backend.log &
tail -f /tmp/frontend.log &
tail -f /tmp/comfyui.log &

# Or use multitail if available
multitail /tmp/backend.log /tmp/comfyui.log
```

### Testing Checklist with Logging

When testing a feature, capture logs:

```bash
# 1. Clear old logs
> /tmp/backend.log
> /tmp/comfyui.log

# 2. Start services with logging
cd /app/charforge-gui/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/backend.log &

# 3. Perform test action (via GUI or CLI)

# 4. Capture logs for analysis
cp /tmp/backend.log /tmp/test_$(date +%Y%m%d_%H%M%S)_backend.log
cp scratch/{name}/timing.log /tmp/test_$(date +%Y%m%d_%H%M%S)_training.log
```

---

## Feature Map: Exact Functionality

### Character Creation

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Name validation | Alphanumeric + underscore/hyphen, max 100 chars | `training.py:create_character()` |
| Image preprocessing | Square padding, resize to train_dim | `training/utilities.py` |
| Work directory | Created at `scratch/{name}/` | `training.py`, `helpers.py` |
| Database record | SQLite row with status tracking | `app/core/database.py` |

### Training Session

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Parameter validation | Steps: 100-10000, LR: 1e-6 to 1e-2, etc. | `training.py:start_training()` |
| Background execution | Uses FastAPI BackgroundTasks | `training.py:run_training_background()` |
| Progress tracking | 0-100% stored in DB, updated during training | `TrainingSession.progress` |
| Status states | pending → running → completed/failed | `TrainingSession.status` |

### Multi-View Generation (MV-Adapter)

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| View angles | 0°, 45°, 90°, 180°, 270°, 315° azimuth | `training/multiview.py` |
| Reference conditioning | Uses input image as reference | MV-Adapter pipeline |
| Background removal | Optional, via rembg | `training/multiview.py` |
| Output | 6 PNG images at 768x768 | `scratch/{name}/sheet/` |

### Emotion/Lighting Variations

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Emotions | Happy, sad, angry, surprised, neutral | `training/emotion_lighting.py` |
| Lighting | Studio, natural, dramatic, soft, rim | `training/workflows/emotion_lighting.py` |
| LivePortrait | Facial expression transfer | ComfyUI custom node |
| IC-Light | Relighting with different conditions | ComfyUI custom node |

### Auto-Captioning

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Model | Google Gemini 2.5 Flash | `LoRACaptioner/` |
| Trigger word | Prepended to all captions (e.g., "ohwx person") | Config in training |
| Output format | `{image_name}.txt` alongside each PNG | `scratch/{name}/sheet/` |
| Retry logic | 3 retries on API failure | `training/utilities.py` |

### LoRA Training (ai-toolkit)

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Base model | FLUX.1-dev (black-forest-labs) | `scripts/character_lora.yaml` |
| LoRA type | Standard LoRA with configurable rank | ai-toolkit config |
| Checkpointing | Save every N steps, keep last M | `advanced_config` |
| Mixed precision | FP16 by default | `advanced_config.mixed_precision` |

### Image Generation (Inference)

| Feature | Description | Files Involved |
|---------|-------------|----------------|
| Pipeline | FLUX.1-dev + trained LoRA | `test_character.py` |
| LoRA weight | Default 0.73, range 0.0-1.0 | `--lora_weight` |
| Prompt optimization | Gemini enhances prompts | `helpers.py:optimize_prompt()` |
| Batch generation | Generate multiple images | `--batch_size` |
| Safety filter | NSFW detection | `inference/safety.py` |

### GUI Features

| Page | Features | Backend Endpoints |
|------|----------|-------------------|
| Dashboard | Overview stats, recent activity | Various GET endpoints |
| Characters | List, create, view details | `/api/training/characters` |
| Training | Start training, view progress, logs | `/api/training/characters/{id}/train` |
| Inference | Generate images, view history | `/api/inference/generate`, `/jobs` |
| Datasets | Manage training datasets | `/api/datasets/*` |
| Settings | API keys, environment config | `/api/settings/*` |

---

## Operational Knowledge (Auto-maintained)

*Last updated: 2025-12-24 (Persistent Volume + Logging Setup)*

### Running the GUI (CLI + Web Interface)

**Start Backend:**
```bash
cd charforge-gui/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Start Frontend (development):**
```bash
cd charforge-gui/frontend
npm run dev
```

**Access Points:**
- Frontend UI: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Log Locations

| Service | Log Location |
|---------|--------------|
| Backend API | Console output or `/tmp/backend.log` (Docker) |
| Frontend | Console output or `/tmp/frontend.log` (Docker) |
| ComfyUI | Console output or `/tmp/comfyui.log` (Docker) |
| Training timing | `./scratch/{character_name}/timing.log` |

### Required Environment Variables

Create `.env` file in project root:
```bash
HF_TOKEN=hf_xxx          # HuggingFace token (REQUIRED)
HF_HOME=/path/to/cache   # HuggingFace cache directory
CIVITAI_API_KEY=xxx      # CivitAI API key (for model downloads)
GOOGLE_API_KEY=xxx       # Google Gemini API key (for captioning)
FAL_KEY=xxx              # fal.ai API key (for upscaling)
```

The GUI stores API keys in the database, configurable via Settings page.

### Common Failure Patterns & Fixes

1. **FastAPI/Pydantic version mismatch**
   - Symptom: `AttributeError: 'FieldInfo' object has no attribute 'in_'`
   - Fix: Ensure `fastapi>=0.115.0` and `pydantic>=2.5.0` (already fixed in requirements.txt)

2. **Rate limit exceeded (429 errors)**
   - Symptom: API returns "Rate limit exceeded. Please try again later."
   - Cause: Built-in rate limiting (3 training sessions/hour, 100 general requests/min)
   - Fix: Restart backend to reset limits, or wait for window to pass

3. **Training session fails immediately**
   - Symptom: Training session status = "failed" within seconds
   - Cause: Missing submodules (ai_toolkit, LoRACaptioner, MV_Adapter)
   - Fix: Run `git submodule update --init --recursive` and `bash setup.sh`

4. **Frontend TypeScript build errors**
   - Symptom: `npm run build` shows type errors
   - Note: These are type annotation warnings, not runtime errors
   - Fix: Use `npx vite build` to skip type checking for dev builds

5. **API proxy not working (404 on /api/*)**
   - Symptom: Frontend can't reach backend
   - Fix: Ensure backend is running on port 8000, frontend on port 5173
   - Vite proxy config is in `frontend/vite.config.ts`

### Changes Made in Fix Session (2025-12-23)

1. **charforge-gui/backend/requirements.txt**
   - Changed `fastapi==0.104.1` to `fastapi>=0.115.0`
   - Changed `pydantic==2.5.0` to `pydantic>=2.5.0`
   - Changed `pydantic-settings==2.1.0` to `pydantic-settings>=2.1.0`

2. **charforge-gui/backend/app/api/training.py**
   - Added missing fields to `TrainingResponse` model: `character_name`, `steps`, `batch_size`, `learning_rate`, `train_dim`, `rank_dim`, `pulidflux_images`
   - Fixed undefined variable bug in `run_training_background()` (lines 345-350)

3. **charforge-gui/frontend/src/services/api.ts**
   - Added missing fields to `TrainingSession` interface
   - Added `input_image_path`, `lora_path`, `preview_image` to `Character` interface
   - Added `SelectedImage` interface for file uploads

4. **charforge-gui/frontend/src/views/settings/SettingsView.vue**
   - Fixed `validationResults` type annotation
   - Fixed `key.replace()` type error by using `String(key)`

5. **charforge-gui/frontend/src/views/TrainingView.vue**
   - Fixed `loadTrainingSessions()` which was hardcoded to return empty array
   - Now properly fetches sessions from API for all characters
