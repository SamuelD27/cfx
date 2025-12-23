# Documentation Changelog

This document records all documentation changes made during the documentation overhaul.

---

## Summary

**Date**: December 2024
**Scope**: Documentation overhaul and Docker packaging
**Goal**: Create operator manual style documentation for local power users focused on high-fidelity identity LoRA training

---

## Files Added

| File | Purpose |
|------|---------|
| `docs/OPERATOR_GUIDE.md` | Step-by-step gold path workflow from image to inference |
| `docs/FIDELITY_PLAYBOOK.md` | Deep guidance on maximizing identity accuracy |
| `docs/ENV_SETUP.md` | Environment variables, API key setup, validation procedures |
| `docs/PIPELINE_OVERVIEW.md` | Architecture diagram and code flow with file references |
| `docs/TROUBLESHOOTING.md` | Expanded error diagnosis with concrete commands |
| `docs/GUI_LOCAL.md` | Local GUI setup and configuration |
| `docs/DOCKER.md` | Docker container build and usage guide |
| `docs/DOCS_CHANGELOG.md` | This file - records all changes |
| `Dockerfile` | GPU-ready Docker image for CharForgex (repo root) |

---

## Files Modified

| File | Changes |
|------|---------|
| `README.md` | Complete rewrite as operator manual hub with: hardware requirements, API dependencies, quickstart, fidelity principles, troubleshooting matrix, file/folder map, documentation links |

---

## Key Improvements

### 1. Hardware Requirements Documented

- Explicit 48GB VRAM requirement with failure modes
- RAM and disk space requirements
- Guidance on what breaks when underpowered

### 2. External API Dependencies Clarified

- All required APIs listed (HuggingFace, Google Gemini, fal.ai, CivitAI)
- Failure modes documented for each
- Environment variable schema provided

### 3. Fidelity-First Guidance

- Reference image selection checklist
- How training data expansion affects identity
- Captioning implications
- Inference prompt patterns for maximum fidelity
- Validation tests for checking identity accuracy

### 4. Troubleshooting Matrix

- Symptom → cause → fix format
- Concrete commands for diagnosis
- Expanded in dedicated troubleshooting doc

### 5. Pipeline Documentation

- ASCII architecture diagram
- Detailed code flow with file:line references
- Data flow showing where files are created

### 6. Docker Support

- Dockerfile added to repo root
- GPU-ready NVIDIA base image
- Volume mount patterns for persistent data
- Build and run documentation

---

## Assumptions Made

### 1. GPU Requirements

- Assumed 48GB VRAM is firm requirement based on README and code analysis
- Consumer GPUs (RTX 3090/4090) noted as potentially working for inference only
- FaceEnhance noted as requiring >48GB based on existing documentation

### 2. API Dependencies

- All listed APIs are required (not optional) based on code analysis
- CivitAI only needed for initial setup (model downloads)
- fal.ai required for both upscaling and PuLID-Flux

### 3. Training Parameters

- Default values taken from `train_character.py` and existing README
- Runtime estimates (30-40 min on L40S) taken from existing README
- Inference timing taken from existing README

### 4. Docker Base Image

- Used `nvidia/cuda:12.4.0-devel-ubuntu22.04` for broad GPU compatibility
- CUDA 12.4 chosen as current stable with good PyTorch support
- Python 3.10 used to match existing requirements

### 5. File Paths

- All paths referenced are verified to exist in codebase
- Relative paths used throughout documentation
- `scratch/` confirmed as primary output location

---

## Open Questions

### 1. Runtime on Other GPUs

Documentation mentions L40S timing. No data available for:
- A100 (likely faster)
- A6000 (likely similar)
- Consumer GPUs (not recommended but may work for inference)

### 2. Lower VRAM Alternatives

Currently no documented way to run on <48GB VRAM. Questions:
- Is there a low-VRAM mode possible?
- Can training be done on cloud with smaller local inference?

### 3. PuLID-Flux Optimal Count

Documentation advises 0-5 PuLID images. This is conservative guidance based on:
- Code allows arbitrary count
- No empirical data on optimal number
- Assumption that more synthetic = more drift risk

### 4. ComfyUI Model Paths in Docker

Workflows may have hardcoded paths that differ from container paths. Not fully tested:
- Custom node installation in container
- Model path compatibility

---

## No Code Changes Made

Per requirements, no source code files were modified:
- No `.py` changes
- No `.js`/`.ts`/`.vue` changes
- No `.sh` changes
- No `.yaml` changes (except documentation)

Only Markdown documentation and the new Dockerfile were added/modified.

---

## Verification

All documentation references verified against actual codebase:

- File paths confirmed to exist
- CLI arguments confirmed against argparse definitions
- Environment variables confirmed against code usage
- Pipeline stages confirmed against code flow

---

[Back to README](../README.md)
