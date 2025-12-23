# CharForgex Dockerfile
# =======================
# GPU-ready container for local power users and RunPod deployment
#
# REQUIREMENTS:
#   - Docker with nvidia-container-toolkit installed
#   - NVIDIA GPU with 48GB+ VRAM
#   - Clone repo with: git clone --recursive (submodules required)
#
# BUILD:
#   docker build -t charforgex .
#
# RUN (local):
#   docker run --gpus all -it \
#     -v $(pwd)/scratch:/app/scratch \
#     -v /path/to/hf_cache:/hf_cache \
#     --env-file .env \
#     charforgex
#
# RUNPOD PORTS:
#   - 22: SSH access
#   - 5173: GUI frontend
#   - 8000: API backend
#   - 8188: ComfyUI (optional)

FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

LABEL maintainer="CharForgex"
LABEL description="GPU-ready container for CharForgex identity LoRA training"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# CUDA architecture list for PyTorch compilation
# Covers most modern NVIDIA GPUs (Ampere, Ada Lovelace, Hopper)
ENV TORCH_CUDA_ARCH_LIST="8.0 8.6 8.9 9.0"

# Python settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies including SSH server
RUN apt-get update && apt-get install --no-install-recommends -y \
    git \
    git-lfs \
    curl \
    wget \
    build-essential \
    cmake \
    python3.10 \
    python3.10-venv \
    python3-pip \
    python3-dev \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    openssh-server \
    ca-certificates \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x for frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure SSH server (passwordless root login)
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitEmptyPasswords no/PermitEmptyPasswords yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PermitEmptyPasswords yes" >> /etc/ssh/sshd_config

# Set Python 3.10 as default
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

# Upgrade pip
RUN python -m pip install --upgrade pip

# Create app directory
WORKDIR /app

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Copy requirements first for layer caching
COPY base_requirements.txt .

# Install base Python dependencies
# Note: PyTorch with CUDA is large; this layer will be cached
RUN uv pip install --system --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

RUN uv pip install --system --no-cache-dir -r base_requirements.txt

# Copy the rest of the application
# IMPORTANT: Build context must include submodules
# Use: git clone --recursive OR git submodule update --init --recursive
COPY . /app

# Verify submodules are present (will fail build if missing)
RUN test -d /app/ai_toolkit && echo "OK: ai_toolkit submodule present" || \
    (echo "ERROR: ai_toolkit submodule missing. Clone with --recursive" && exit 1)
RUN test -d /app/LoRACaptioner && echo "OK: LoRACaptioner submodule present" || \
    (echo "ERROR: LoRACaptioner submodule missing. Clone with --recursive" && exit 1)

# Create directories for runtime data
RUN mkdir -p /app/scratch /app/ComfyUI/models/checkpoints /app/ComfyUI/models/loras

# Install backend dependencies
RUN cd /app/charforge-gui/backend && \
    uv pip install --system --no-cache-dir -r requirements.txt

# Install frontend dependencies
RUN cd /app/charforge-gui/frontend && npm install

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Set working directory
WORKDIR /app

# Default HF_HOME location (can be overridden with volume mount)
ENV HF_HOME=/hf_cache

# Expose ports
# 22: SSH access
# 8000: FastAPI backend
# 5173: Vue frontend
# 8188: ComfyUI (if running manually)
EXPOSE 22 8000 5173 8188

# Use entrypoint script (starts SSH, keeps container alive)
CMD ["/app/docker-entrypoint.sh"]
