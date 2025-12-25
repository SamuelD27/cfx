#!/bin/bash
set -e  # Exit on any error

echo "🚀 Starting setup process..."

# Set cache directories
export PIP_CACHE_DIR="$(pwd)/.cache/pip"
export UV_CACHE_DIR="$(pwd)/.cache/uv"
mkdir -p "$PIP_CACHE_DIR" "$UV_CACHE_DIR"

# Detect if running in Docker (dependencies pre-installed)
IN_DOCKER=false
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
fi

# Check if nvdiffrast is already installed (indicates Docker with pre-built deps)
DEPS_PREINSTALLED=false
if python3 -c "import nvdiffrast.torch" 2>/dev/null; then
    DEPS_PREINSTALLED=true
fi

if [ "$DEPS_PREINSTALLED" = true ]; then
    echo "✅ Dependencies already installed (Docker image with pre-built deps)"
    echo "📦 Skipping venv creation, using system Python..."

    # Just run install.py for submodule setup and model downloads
    echo "📦 Running installation script for submodules and models..."
    python3 install.py

else
    echo "📦 Installing dependencies from scratch..."

    # Install minimal system dependencies needed for uv
    echo "📦 Installing system dependencies..."
    apt-get update && apt-get install -y curl git

    # Install uv
    echo "🔧 Installing uv package installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    source $HOME/.local/bin/env 2>/dev/null || true

    # Create and activate virtual environment
    echo "🔧 Creating virtual environment..."
    uv venv
    source .venv/bin/activate

    # Install setuptools first (required for nvdiffrast)
    echo "📦 Installing setuptools..."
    pip install --upgrade pip setuptools wheel

    # Install nvdiffrast FIRST with pip (not uv) - requires --no-build-isolation
    echo "📦 Installing nvdiffrast (requires special build flags)..."
    pip install git+https://github.com/NVlabs/nvdiffrast.git --no-build-isolation

    # Install remaining packages with uv (nvdiffrast will be skipped since already installed)
    echo "📦 Installing Python packages..."
    uv pip install -r base_requirements.txt

    # Run the main Python install script
    echo "📦 Running main installation script..."
    python install.py
fi

echo "✨ Setup complete!"
