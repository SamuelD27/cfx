# Environment Setup Guide

[Back to README](../README.md)

This document covers the complete environment configuration, API key setup, and validation procedures.

---

## Environment Variables Schema

Create a `.env` file in the repository root with the following variables:

```bash
# =============================================================================
# REQUIRED: HuggingFace
# =============================================================================
# Get from: https://huggingface.co/settings/tokens
# Permissions needed: Read access to gated models
# Used for: Downloading FLUX.1-dev, transformers models, embeddings
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Path where HuggingFace models are cached
# Should have 100GB+ free space
# Used by: All model downloads and loads
HF_HOME=/path/to/huggingface/cache

# =============================================================================
# REQUIRED: Google Gemini
# =============================================================================
# Get from: https://aistudio.google.com/app/apikey
# Used for: Image captioning (LoRACaptioner), prompt generation (PuLID-Flux)
# Rate limits: 15 requests/minute (free tier)
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxx

# =============================================================================
# REQUIRED: fal.ai
# =============================================================================
# Get from: https://fal.ai/dashboard/keys
# Used for: ESRGAN upscaling, PuLID-Flux image generation
# Billing: Pay-per-use, add credits first
FAL_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# =============================================================================
# REQUIRED FOR SETUP: CivitAI
# =============================================================================
# Get from: https://civitai.com/user/account (API Keys section)
# Used for: Downloading checkpoint models during setup.sh
# Only needed during initial setup, not runtime
CIVITAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# =============================================================================
# OPTIONAL: Application Path
# =============================================================================
# Override if running from non-standard location
# Default: Current working directory
# APP_PATH=/path/to/CharForgex
```

---

## API Key Setup: Step by Step

### 1. HuggingFace Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: `charforgex` (or similar)
4. Role: **Read**
5. Copy the token starting with `hf_`

**Additional Step**: Accept FLUX.1-dev license
1. Go to https://huggingface.co/black-forest-labs/FLUX.1-dev
2. Click "Agree and access repository"
3. Wait for approval (usually instant)

### 2. Google Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Select or create a Google Cloud project
4. Copy the key starting with `AIzaSy`

**Note**: Free tier has 15 requests/minute limit. The pipeline has built-in retry logic.

### 3. fal.ai API Key

1. Go to https://fal.ai/dashboard
2. Sign in/create account
3. Go to "API Keys" section
4. Create new key
5. Copy the UUID-format key
6. **Important**: Add credits (billing section) - operations cost ~$0.01-0.10 each

### 4. CivitAI API Key

1. Go to https://civitai.com/user/account
2. Scroll to "API Keys" section
3. Click "Add API Key"
4. Name it and copy the key

---

## HF_HOME Configuration

The `HF_HOME` variable determines where all HuggingFace models are cached. This is critical for:

- Avoiding re-downloads (~50GB of models)
- Sharing cache across multiple runs
- Managing disk space

### Recommended Setup

```bash
# Create dedicated cache directory
mkdir -p /data/huggingface_cache

# Set in .env
HF_HOME=/data/huggingface_cache

# Verify space
df -h /data/huggingface_cache
# Should show 100GB+ available
```

### What Gets Cached

| Model | Approximate Size |
|-------|------------------|
| FLUX.1-dev | ~23GB |
| Juggernaut-XL | ~6GB |
| BiRefNet | ~2GB |
| MV-Adapter | ~1GB |
| NSFW detector | ~0.5GB |
| Various transformers | ~5GB |
| **Total** | ~40-50GB |

---

## Preflight Check Script

Run this before first use to validate your environment:

```bash
#!/bin/bash
# Save as: preflight_check.sh

echo "=== CharForgex Preflight Check ==="

# Check .env exists
if [ ! -f .env ]; then
    echo "FAIL: .env file not found"
    exit 1
fi
echo "OK: .env file exists"

# Source .env
source .env

# Check HF_TOKEN
if [ -z "$HF_TOKEN" ]; then
    echo "FAIL: HF_TOKEN not set"
else
    echo "OK: HF_TOKEN is set (${HF_TOKEN:0:10}...)"
fi

# Check HF_HOME
if [ -z "$HF_HOME" ]; then
    echo "FAIL: HF_HOME not set"
elif [ ! -d "$HF_HOME" ]; then
    echo "WARN: HF_HOME directory does not exist: $HF_HOME"
    echo "      Will be created on first run"
else
    SPACE=$(df -BG "$HF_HOME" | tail -1 | awk '{print $4}' | tr -d 'G')
    echo "OK: HF_HOME exists with ${SPACE}GB free"
fi

# Check GOOGLE_API_KEY
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "FAIL: GOOGLE_API_KEY not set"
else
    echo "OK: GOOGLE_API_KEY is set (${GOOGLE_API_KEY:0:10}...)"
fi

# Check FAL_KEY
if [ -z "$FAL_KEY" ]; then
    echo "FAIL: FAL_KEY not set"
else
    echo "OK: FAL_KEY is set (${FAL_KEY:0:8}...)"
fi

# Check CIVITAI_API_KEY
if [ -z "$CIVITAI_API_KEY" ]; then
    echo "WARN: CIVITAI_API_KEY not set (only needed for setup)"
else
    echo "OK: CIVITAI_API_KEY is set"
fi

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    if [ "$GPU_MEM" -lt 48000 ]; then
        echo "WARN: GPU has ${GPU_MEM}MB VRAM (48GB+ recommended)"
    else
        echo "OK: GPU has ${GPU_MEM}MB VRAM"
    fi
else
    echo "FAIL: nvidia-smi not found"
fi

# Check Python
if command -v python &> /dev/null; then
    PY_VER=$(python --version 2>&1)
    echo "OK: Python version: $PY_VER"
else
    echo "FAIL: Python not found"
fi

# Check venv
if [ -d ".venv" ]; then
    echo "OK: Virtual environment exists"
else
    echo "WARN: .venv not found (run setup.sh first)"
fi

echo "=== Preflight check complete ==="
```

Run with:
```bash
chmod +x preflight_check.sh
./preflight_check.sh
```

---

## Validating API Keys

### Test HuggingFace Token

```bash
source .venv/bin/activate
python -c "
from huggingface_hub import HfApi
api = HfApi()
try:
    user = api.whoami()
    print(f'OK: Logged in as {user[\"name\"]}')
except Exception as e:
    print(f'FAIL: {e}')
"
```

### Test Google Gemini Key

```bash
source .venv/bin/activate
python -c "
import os
from google import genai
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
try:
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents='Hello'
    )
    print('OK: Gemini API responding')
except Exception as e:
    print(f'FAIL: {e}')
"
```

### Test fal.ai Key

```bash
source .venv/bin/activate
python -c "
import fal_client
try:
    # Simple connectivity test
    print('OK: fal_client imported (key will be validated on first use)')
except Exception as e:
    print(f'FAIL: {e}')
"
```

---

## Common Environment Issues

### Issue: `HF_TOKEN` Not Recognized

**Symptom**: "Token is not valid" or 401 errors during model download

**Causes**:
1. Token copied incorrectly (extra spaces/newlines)
2. Token expired or revoked
3. Token doesn't have read access

**Fix**:
```bash
# Verify token format (should start with hf_)
echo $HF_TOKEN | head -c 10

# Regenerate at https://huggingface.co/settings/tokens
```

### Issue: `HF_HOME` Permission Denied

**Symptom**: Permission errors when downloading models

**Fix**:
```bash
# Check ownership
ls -la $HF_HOME

# Fix permissions
sudo chown -R $USER:$USER $HF_HOME
```

### Issue: Google Gemini Rate Limits

**Symptom**: 429 errors or "Resource exhausted"

**Causes**:
1. Free tier limit (15 req/min)
2. Running multiple pipelines simultaneously

**Fix**: The pipeline has built-in retry logic. If persistent:
```bash
# Wait and retry
sleep 60
# Or upgrade to paid tier
```

### Issue: fal.ai "Insufficient Credits"

**Symptom**: 402 Payment Required errors

**Fix**:
1. Go to https://fal.ai/dashboard/billing
2. Add credits ($10 minimum recommended)
3. Retry

---

## Environment File Template

Copy this to `.env` and fill in values:

```bash
# CharForgex Environment Configuration
# =====================================

# HuggingFace (REQUIRED)
HF_TOKEN=
HF_HOME=

# Google Gemini (REQUIRED)
GOOGLE_API_KEY=

# fal.ai (REQUIRED)
FAL_KEY=

# CivitAI (REQUIRED for setup only)
CIVITAI_API_KEY=
```

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md)
