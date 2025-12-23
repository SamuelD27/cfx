# Docker Guide

[Back to README](../README.md)

This document covers building and running CharForgex in a Docker container.

---

## Prerequisites

1. **Docker** installed
2. **nvidia-container-toolkit** installed (for GPU access)
3. **NVIDIA GPU** with 48GB+ VRAM
4. Repository cloned with submodules:
   ```bash
   git clone --recursive https://github.com/your-repo/CharForgex.git
   ```

---

## Exposed Ports

| Port | Service | Required for RunPod |
|------|---------|---------------------|
| **22** | SSH server | Yes - remote access |
| **5173** | Vue.js frontend (GUI) | Yes - GUI access |
| **8000** | FastAPI backend | Yes - API for GUI |
| **8188** | ComfyUI | Optional |

---

## Building the Image

```bash
cd CharForgex

# Build the image
docker build -t charforgex .
```

**Build time**: 10-20 minutes (first time, depends on network speed)

**Image size**: ~15-20GB (includes PyTorch with CUDA)

### Build Notes

- Submodules must be present in build context
- If build fails with "submodule missing", run:
  ```bash
  git submodule update --init --recursive
  docker build -t charforgex .
  ```

---

## Running with GPU

### Basic Run (Interactive)

```bash
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  --env-file .env \
  charforgex bash
```

### Volume Mounts Explained

| Mount | Purpose | Required |
|-------|---------|----------|
| `./scratch:/app/scratch` | Character data (LoRAs, outputs) | Yes - data persists |
| `/path/to/hf_cache:/hf_cache` | HuggingFace model cache | Yes - avoids re-downloads |
| `.env` passed via `--env-file` | API keys | Yes - required for operation |

### Environment Variables

The container expects these environment variables (pass via `.env` file):

```bash
HF_TOKEN=hf_xxxxxxxxxxxx
HF_HOME=/hf_cache           # Must match volume mount
GOOGLE_API_KEY=AIzaSyxxxxx
FAL_KEY=xxxxxxxx
CIVITAI_API_KEY=xxxxxxxx   # Only for setup
```

---

## First Run: Setup

Inside the container, run setup once to download models:

```bash
# Start container
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  --env-file .env \
  charforgex bash

# Inside container
bash setup.sh
```

**Download size**: ~50GB of models
**Time**: 20-60 minutes depending on network

The models are saved to `/hf_cache` (your mounted volume), so they persist between container runs.

---

## Training

```bash
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  -v /path/to/input/image.jpg:/input/image.jpg:ro \
  --env-file .env \
  charforgex \
  python train_character.py --name "character" --input "/input/image.jpg"
```

Or interactively:

```bash
# Start container
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  --env-file .env \
  charforgex bash

# Inside container
python train_character.py --name "character" --input "/app/scratch/my_image.jpg"
```

---

## Inference

```bash
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  --env-file .env \
  charforgex \
  python test_character.py --character_name "character" --prompt "Your prompt"
```

Outputs are saved to `./scratch/character/output/` (on host via volume mount).

---

## GUI (Optional)

To run the GUI inside Docker:

```bash
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v /path/to/hf_cache:/hf_cache \
  --env-file .env \
  -p 5173:5173 \
  -p 8000:8000 \
  charforgex bash

# Inside container
cd charforge-gui
./start-dev.sh
```

Access at http://localhost:5173 on host.

**Note**: GUI startup takes a minute to install frontend dependencies.

---

## Complete Example Session

```bash
# 1. Clone repo with submodules
git clone --recursive https://github.com/your-repo/CharForgex.git
cd CharForgex

# 2. Create .env file with API keys
cat > .env << 'EOF'
HF_TOKEN=hf_your_token_here
HF_HOME=/hf_cache
GOOGLE_API_KEY=AIzaSyYourKeyHere
FAL_KEY=your-fal-key-here
CIVITAI_API_KEY=your-civitai-key-here
EOF

# 3. Build image
docker build -t charforgex .

# 4. Create persistent directories
mkdir -p scratch hf_cache

# 5. First run: setup (downloads models)
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v $(pwd)/hf_cache:/hf_cache \
  --env-file .env \
  charforgex bash -c "bash setup.sh"

# 6. Train a character
# (copy your reference image to scratch/ first)
cp /path/to/my_photo.jpg scratch/

docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v $(pwd)/hf_cache:/hf_cache \
  --env-file .env \
  charforgex \
  python train_character.py --name "mycharacter" --input "/app/scratch/my_photo.jpg"

# 7. Run inference
docker run --gpus all -it \
  -v $(pwd)/scratch:/app/scratch \
  -v $(pwd)/hf_cache:/hf_cache \
  --env-file .env \
  charforgex \
  python test_character.py --character_name "mycharacter" --prompt "A portrait"

# 8. Find outputs
ls scratch/mycharacter/output/
```

---

## RunPod Deployment

### Template Configuration

When creating a RunPod template, configure these ports:

| Port | Type | Purpose |
|------|------|---------|
| 22 | TCP | SSH access |
| 5173 | HTTP | GUI frontend |
| 8000 | HTTP | API backend |
| 8188 | HTTP | ComfyUI (optional) |

### Environment Variables for RunPod

Set these in your RunPod template:

```
HF_TOKEN=hf_xxxxxxxxxxxx
HF_HOME=/hf_cache
GOOGLE_API_KEY=AIzaSyxxxxx
FAL_KEY=xxxxxxxx
CIVITAI_API_KEY=xxxxxxxx
```

### SSH Access

The container runs an SSH server on port 22 with **no password required**.

**Connect:**
```bash
ssh root@<pod-ip> -p <mapped-port>
```

Just press Enter if prompted for a password (it's empty).

### Starting the GUI on RunPod

After connecting via SSH:

```bash
cd /app/charforge-gui
./start-dev.sh
```

Then access via the mapped port for 5173 in your browser.

---

## What Is and Is Not Supported

### Supported

- Training via `train_character.py`
- Inference via `test_character.py`
- GUI (with port mapping)
- All API integrations (HuggingFace, fal.ai, Gemini)
- Persistent data via volume mounts
- SSH access (port 22)
- RunPod deployment

### Caveats

- **ComfyUI paths**: The container uses `/app/ComfyUI/` for ComfyUI. Model paths in workflows assume this location.
- **First run is slow**: Model downloads take 20-60 minutes on first setup.
- **Large image**: The Docker image is 15-20GB due to PyTorch+CUDA.
- **GPU required**: Container will not function without `--gpus all`.

### Not Tested/Supported

- Running without GPU (CPU-only mode)
- Multi-GPU training
- Kubernetes deployment
- Docker Compose orchestration

---

## Troubleshooting

### nvidia-container-toolkit Not Installed

**Error**: `docker: Error response from daemon: could not select device driver`

**Fix**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### CUDA Out of Memory

Same as host system - requires 48GB+ VRAM. See [Troubleshooting](TROUBLESHOOTING.md#vram-issues).

### Submodule Missing During Build

**Error**: `ERROR: ai_toolkit submodule missing`

**Fix**:
```bash
git submodule update --init --recursive
docker build -t charforgex .
```

### Permission Denied on Volume Mount

**Fix**:
```bash
# On host
chmod -R 777 scratch hf_cache
```

Or run container as your user:
```bash
docker run --gpus all -it --user $(id -u):$(id -g) ...
```

---

## Resource Recommendations

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Host RAM | 32GB | 64GB+ |
| GPU VRAM | 48GB | 48GB+ |
| Disk (image) | 25GB | 30GB |
| Disk (models) | 60GB | 100GB+ |
| Disk (scratch) | 10GB | 50GB+ |

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md)
