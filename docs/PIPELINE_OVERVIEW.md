# Pipeline Overview

[Back to README](../README.md)

This document provides a visual overview of the CharForgex pipeline architecture and code flow.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CharForgex Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT                          TRAINING                        INFERENCE   │
│  ─────                          ────────                        ─────────   │
│                                                                              │
│  ┌─────────┐    ┌─────────────────────────────────┐    ┌─────────────────┐  │
│  │Reference│───►│      train_character.py         │    │test_character.py│  │
│  │ Image   │    │                                 │    │                 │  │
│  └─────────┘    │  ┌───────────────────────────┐  │    │  ┌───────────┐  │  │
│                 │  │   generate_sheet.py       │  │    │  │ FluxPipe  │  │  │
│                 │  │                           │  │    │  │ + LoRA    │  │  │
│                 │  │  ┌─────────┐ ┌─────────┐  │  │    │  └─────┬─────┘  │  │
│                 │  │  │Multiview│ │Emotion/ │  │  │    │        │        │  │
│                 │  │  │MV-Adapt │ │Lighting │  │  │    │  ┌─────▼─────┐  │  │
│                 │  │  └────┬────┘ └────┬────┘  │  │    │  │  Safety   │  │  │
│                 │  │       │           │       │  │    │  │  Checker  │  │  │
│                 │  │  ┌────▼───────────▼────┐  │  │    │  └─────┬─────┘  │  │
│                 │  │  │   Upscale (fal.ai)  │  │  │    │        │        │  │
│                 │  │  └──────────┬──────────┘  │  │    │  ┌─────▼─────┐  │  │
│                 │  │             │             │  │    │  │Face       │  │  │
│                 │  │  ┌──────────▼──────────┐  │  │    │  │Enhance    │  │  │
│                 │  │  │  Caption (Gemini)   │  │  │    │  │(optional) │  │  │
│                 │  │  └──────────┬──────────┘  │  │    │  └─────┬─────┘  │  │
│                 │  └─────────────┼─────────────┘  │    │        │        │  │
│                 │                │                │    │        ▼        │  │
│                 │  ┌─────────────▼─────────────┐  │    │   ┌─────────┐   │  │
│                 │  │     ai-toolkit LoRA      │  │    │   │ OUTPUT  │   │  │
│                 │  │        Training          │  │    │   │ Images  │   │  │
│                 │  └─────────────┬─────────────┘  │    │   └─────────┘   │  │
│                 │                │                │    │                 │  │
│                 │                ▼                │    │                 │  │
│                 │  ┌─────────────────────────────┐│    │                 │  │
│                 │  │    char.safetensors        │├───►│                 │  │
│                 │  │         (LoRA)             ││    │                 │  │
│                 │  └─────────────────────────────┘│    │                 │  │
│                 └─────────────────────────────────┘    └─────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Training Pipeline Detail

```
train_character.py
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  build_character(config)                                    [Line 259]    │
│                                                                           │
│  1. Create work_dir: ./scratch/{name}/                                    │
│  2. Initialize timing log                                                 │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ build_charsheet(config)                                  [Line 72]  │  │
│  │                                                                     │  │
│  │  └──► generate_char_sheet()   training/generate_sheet.py [Line 157]│  │
│  │        │                                                           │  │
│  │        ├── Preprocess: rectangle_to_square, resize_if_large       │  │
│  │        │   training/utilities.py [Lines 20-45]                     │  │
│  │        │                                                           │  │
│  │        ├── Caption: generate_caption() via Gemini                  │  │
│  │        │   training/utilities.py [Line 145]                        │  │
│  │        │                                                           │  │
│  │        ├── Multi-view: create_multiview_images()                   │  │
│  │        │   training/multiview.py [Line 203]                        │  │
│  │        │   └── MV-Adapter on SDXL (Juggernaut-XL)                  │  │
│  │        │   └── Upscale via fal.ai ESRGAN                           │  │
│  │        │                                                           │  │
│  │        ├── Emotion/Lighting: generate_emotion_lighting()           │  │
│  │        │   training/emotion_lighting.py [Line 9]                   │  │
│  │        │   └── IC-Light for lighting variations                    │  │
│  │        │   └── LivePortrait for expression variations              │  │
│  │        │                                                           │  │
│  │        ├── (Optional) PuLID-Flux: generate_synthetic_images()      │  │
│  │        │   training/pulid_flux_images.py [Line 258]                │  │
│  │        │                                                           │  │
│  │        └── Gather: gather_sheet_images()                           │  │
│  │            training/generate_sheet.py [Line 47]                    │  │
│  │                                                                     │  │
│  │  └──► run_captioner.sh (isolated venv)                             │  │
│  │        scripts/run_captioner.sh                                     │  │
│  │        └── LoRACaptioner with Gemini                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  3. Clear CUDA memory                                                     │
│                                                                           │
│  4. Preprocess dataset: preprocess_dataset_before_training()              │
│     training/utilities.py [Line 380]                                      │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ train_lora(config)                                       [Line 167] │  │
│  │                                                                     │  │
│  │  └── Create config.yaml from scripts/character_lora.yaml           │  │
│  │  └── Run ai-toolkit via scripts/run_ai_toolkit.sh (isolated venv)  │  │
│  │  └── Output: ./scratch/{name}/char/char.safetensors                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Inference Pipeline Detail

```
test_character.py
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  main()                                                      [Line 220]   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ LoRAImageGen.generate()                                  [Line 92]  │  │
│  │                                                                     │  │
│  │  1. Set work_dir: ./scratch/{character_name}/                       │  │
│  │                                                                     │  │
│  │  2. (Optional) Optimize prompt                                      │  │
│  │     └── optimize_prompt()   helpers.py [Line 72]                    │  │
│  │         └── Runs LoRACaptioner/prompt.py                            │  │
│  │                                                                     │  │
│  │  3. Find LoRA                                                       │  │
│  │     └── find_character_lora()   helpers.py [Line 36]                │  │
│  │         └── Returns ./scratch/{name}/char/char.safetensors          │  │
│  │                                                                     │  │
│  │  4. Prepare model                                                   │  │
│  │     └── LoRAImageGen.prepare()                           [Line 26]  │  │
│  │         └── Load FluxPipeline from HuggingFace                      │  │
│  │         └── Apply optimizations (fuse_qkv_projections)              │  │
│  │         └── Load SafetyChecker                                      │  │
│  │                                                                     │  │
│  │  5. Generate images                                                 │  │
│  │     └── LoRAImageGen.do_inference()                      [Line 47]  │  │
│  │         └── Load LoRA weights                                       │  │
│  │         └── Run FluxPipeline                                        │  │
│  │         └── Output: List of JPEG bytes                              │  │
│  │                                                                     │  │
│  │  6. Save to files                                                   │  │
│  │     └── save_images_to_files()                          [Line 199]  │  │
│  │         └── Output: ./scratch/{name}/output/*.jpg                   │  │
│  │                                                                     │  │
│  │  7. (Optional) Face enhancement                                     │  │
│  │     └── FaceEnhancer.process()                                      │  │
│  │         inference/postprocess.py [Line 24]                          │  │
│  │         └── ComfyUI face_enhance workflow                           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ LoRAImageGen.check_safety()                             [Line 182]  │  │
│  │                                                                     │  │
│  │  └── SafetyChecker.check_multiple()                                 │  │
│  │      inference/safety.py [Line 102]                                 │  │
│  │      └── NSFW detection using Falconsai model                       │  │
│  │      └── Replace violations with blank placeholders                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Key Source Files Reference

### Entrypoints

| File | Purpose |
|------|---------|
| [`train_character.py`](../train_character.py) | Main training CLI |
| [`test_character.py`](../test_character.py) | Main inference CLI |
| [`setup.sh`](../setup.sh) | One-time setup script |
| [`install.py`](../install.py) | Installation logic |

### Training Pipeline

| File | Purpose |
|------|---------|
| [`training/generate_sheet.py`](../training/generate_sheet.py) | Orchestrates sheet generation |
| [`training/multiview.py`](../training/multiview.py) | MV-Adapter multi-view generation |
| [`training/emotion_lighting.py`](../training/emotion_lighting.py) | Emotion/lighting orchestration |
| [`training/pulid_flux_images.py`](../training/pulid_flux_images.py) | PuLID-Flux synthetic generation |
| [`training/utilities.py`](../training/utilities.py) | Image utilities, captioning |
| [`training/workflows/emotion_lighting.py`](../training/workflows/emotion_lighting.py) | ComfyUI emotion/lighting workflow |
| [`training/workflows/upscale_grid_image.py`](../training/workflows/upscale_grid_image.py) | ComfyUI upscaling workflow |

### Inference Pipeline

| File | Purpose |
|------|---------|
| [`inference/safety.py`](../inference/safety.py) | NSFW detection |
| [`inference/postprocess.py`](../inference/postprocess.py) | Face enhancement wrapper |
| [`inference/workflows/face_enhance.py`](../inference/workflows/face_enhance.py) | ComfyUI face enhancement |

### Utilities and Scripts

| File | Purpose |
|------|---------|
| [`helpers.py`](../helpers.py) | Subprocess, LoRA finding, prompt optimization |
| [`scripts/character_lora.yaml`](../scripts/character_lora.yaml) | LoRA training config template |
| [`scripts/run_ai_toolkit.sh`](../scripts/run_ai_toolkit.sh) | ai-toolkit runner (isolated venv) |
| [`scripts/run_captioner.sh`](../scripts/run_captioner.sh) | LoRACaptioner runner (isolated venv) |
| [`scripts/serve_lora.py`](../scripts/serve_lora.py) | FastAPI LoRA serving |
| [`scripts/run_comfy.py`](../scripts/run_comfy.py) | Manual ComfyUI launch |

### Git Submodules

| Submodule | Purpose |
|-----------|---------|
| [`ai_toolkit/`](../ai_toolkit/) | LoRA training (ostris/ai-toolkit) |
| [`LoRACaptioner/`](../LoRACaptioner/) | Auto-captioning |
| [`MV_Adapter/`](../MV_Adapter/) | Multi-view generation |
| [`ComfyUI/`](../ComfyUI/) | Workflow execution engine |
| [`ComfyUI_AutoCropFaces/`](../ComfyUI_AutoCropFaces/) | Face cropping utilities |

---

## Data Flow: Where Files Go

```
INPUT:
  /path/to/reference.jpg
        │
        ▼
TRAINING ARTIFACTS:
  ./scratch/{character_name}/
  ├── sheet/
  │   ├── original.png              ← Copy of input
  │   ├── input.png                 ← Preprocessed (square, resized)
  │   ├── upscaled_multiview_0.png  ← Front view
  │   ├── upscaled_multiview_1.png  ← 45° left
  │   ├── upscaled_multiview_2.png  ← 90° left (profile)
  │   ├── upscaled_multiview_3.png  ← Back
  │   ├── upscaled_multiview_4.png  ← 90° right
  │   ├── upscaled_multiview_5.png  ← 45° right
  │   ├── upscaled_lighting_0.png   ← Overcast lighting
  │   ├── upscaled_lighting_1.png   ← Sunset lighting
  │   ├── upscaled_lighting_2.png   ← Nightclub lighting
  │   ├── upscaled_lighting_3.png   ← Desert lighting
  │   ├── upscaled_emotions_1.png   ← Eyes closed
  │   ├── upscaled_emotions_3.png   ← Laughing
  │   ├── face_upscaled.png         ← High-res face crop
  │   ├── *.txt                     ← Caption for each image
  │   ├── image_info.json           ← Image metadata
  │   └── trash/                    ← Unused intermediates
  ├── char/
  │   └── char.safetensors          ← THE TRAINED LORA
  ├── config.yaml                   ← Training config used
  └── timing.log                    ← Stage timing data
        │
        ▼
INFERENCE OUTPUT:
  ./scratch/{character_name}/output/
  ├── {name}_{timestamp}_0.jpg
  ├── {name}_{timestamp}_1.jpg
  ├── {name}_{timestamp}_2.jpg
  └── {name}_{timestamp}_3.jpg
```

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md)
