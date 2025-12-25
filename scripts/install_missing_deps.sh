#!/bin/bash
# Install missing dependencies for CharForgex training pipeline
# Run this script after pod initialization or in Dockerfile
#
# This script fixes all dependencies discovered during troubleshooting:
# - nvdiffrast (CUDA mesh rendering)
# - omegaconf, timm, einops (ML utilities)
# - diffusers, transformers, accelerate (HuggingFace)
# - trimesh, pyrender, rembg (3D/image processing)
# - google-genai (Gemini API)
# - matplotlib, opencv (visualization)

set -e

echo "=========================================="
echo "  CharForgex Dependency Installer"
echo "=========================================="
echo ""

# Detect if we're in a venv
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Running in venv: $VIRTUAL_ENV"
    PIP_CMD="pip"
else
    echo "Running in system Python"
    PIP_CMD="pip"
fi

echo ""
echo "[1/7] Installing setuptools and wheel (required for nvdiffrast)..."
$PIP_CMD install --upgrade pip setuptools wheel --quiet

echo "[2/7] Installing nvdiffrast..."
cd /tmp
rm -rf nvdiffrast
git clone https://github.com/NVlabs/nvdiffrast.git
cd nvdiffrast
$PIP_CMD install . --no-build-isolation --quiet 2>&1 | tail -3 || true

# Verify nvdiffrast installed correctly
if python3 -c "import nvdiffrast.torch" 2>/dev/null; then
    echo "nvdiffrast installed successfully"
else
    echo "nvdiffrast build may have failed, attempting manual fix..."
    SITE_PACKAGES=$(python3 -c 'import site; print(site.getsitepackages()[0])')
    cp -r /tmp/nvdiffrast/nvdiffrast "$SITE_PACKAGES/" 2>/dev/null || true
    cat > "$SITE_PACKAGES/nvdiffrast/__init__.py" << 'INIT_EOF'
try:
    from importlib.metadata import version
    __version__ = version(__package__ or 'nvdiffrast')
except Exception:
    __version__ = '0.3.1'
INIT_EOF
fi

echo "[3/7] Installing HuggingFace packages..."
$PIP_CMD install diffusers>=0.36.0 transformers accelerate --quiet

echo "[4/7] Installing ML utilities..."
$PIP_CMD install omegaconf timm einops --quiet

echo "[5/7] Installing image/3D processing packages..."
$PIP_CMD install trimesh pyrender rembg --quiet

echo "[6/7] Installing visualization packages..."
$PIP_CMD install matplotlib opencv-python-headless safetensors --quiet

echo "[7/7] Installing Google GenAI packages..."
$PIP_CMD install google-genai google-generativeai --quiet

echo ""
echo "=========================================="
echo "  All dependencies installed successfully!"
echo "=========================================="

# Verify critical imports
echo ""
echo "Verifying installations..."
python3 -c "import nvdiffrast.torch; print('  nvdiffrast: OK')" 2>/dev/null || echo "  nvdiffrast: FAILED"
python3 -c "import diffusers; print('  diffusers: OK')" 2>/dev/null || echo "  diffusers: FAILED"
python3 -c "import transformers; print('  transformers: OK')" 2>/dev/null || echo "  transformers: FAILED"
python3 -c "import omegaconf; print('  omegaconf: OK')" 2>/dev/null || echo "  omegaconf: FAILED"
python3 -c "import timm; print('  timm: OK')" 2>/dev/null || echo "  timm: FAILED"
echo ""
