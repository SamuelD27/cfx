#!/bin/bash
# CharForgex Docker Entrypoint
# ============================
# Starts SSH, GUI services, and keeps container alive for RunPod/cloud deployment
# Automatically runs first-time setup if not already completed

set -e

SETUP_MARKER="/app/.setup_complete"
SETUP_LOG="/tmp/setup.log"

# Generate SSH host keys if they don't exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "[entrypoint] Generating SSH host keys..."
    ssh-keygen -A
fi

# Remove root password (passwordless login)
passwd -d root

# Start SSH daemon
echo "[entrypoint] Starting SSH server on port 22 (no password required)..."
/usr/sbin/sshd

# Load environment variables from root .env
if [ -f /app/.env ]; then
    echo "[entrypoint] Loading environment variables from /app/.env..."
    set -a
    source /app/.env
    set +a
else
    # Create .env from environment variables if they exist (from --env-file or -e flags)
    if [ -n "$HF_TOKEN" ] || [ -n "$CIVITAI_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
        echo "[entrypoint] Creating /app/.env from environment variables..."
        cat > /app/.env << ENVEOF
HF_TOKEN=${HF_TOKEN:-}
HF_HOME=${HF_HOME:-/hf_cache}
CIVITAI_API_KEY=${CIVITAI_API_KEY:-}
GOOGLE_API_KEY=${GOOGLE_API_KEY:-}
FAL_KEY=${FAL_KEY:-}
ENVEOF
        echo "[entrypoint] Created /app/.env with provided credentials"
    else
        echo "[entrypoint] WARNING: No .env file found and no API keys in environment."
        echo "[entrypoint] Model downloads may fail. Provide keys via --env-file or -e flags."
    fi
fi

# ============================================================
# FIRST-TIME SETUP (runs once, downloads ~50GB of models)
# ============================================================
if [ ! -f "$SETUP_MARKER" ]; then
    echo ""
    echo "================================================="
    echo "  FIRST-TIME SETUP - This may take 30-60 minutes"
    echo "  Downloading models and dependencies (~50GB)"
    echo "  Progress logged to: $SETUP_LOG"
    echo "================================================="
    echo ""

    cd /app

    # Run setup.sh and capture output
    echo "[entrypoint] Running setup.sh..."
    if bash setup.sh 2>&1 | tee "$SETUP_LOG"; then
        # Mark setup as complete only on success
        date > "$SETUP_MARKER"
        echo "[entrypoint] Setup completed successfully!"
    else
        echo "[entrypoint] ERROR: Setup failed! Check $SETUP_LOG for details."
        echo "[entrypoint] You can re-run manually with: cd /app && bash setup.sh"
        # Continue anyway so user can SSH in and debug
    fi
fi

# Create backend .env with auth disabled if it doesn't exist
if [ ! -f /app/charforge-gui/backend/.env ]; then
    echo "[entrypoint] Creating backend .env with auth disabled..."
    cat > /app/charforge-gui/backend/.env << 'BACKEND_ENV'
# CharForge GUI Backend Configuration
# Authentication DISABLED for local power user workflow
ENABLE_AUTH=false
ALLOW_REGISTRATION=false
DEFAULT_USER_ID=1
SECRET_KEY=charforge-local-dev-key-not-for-production
DATABASE_URL=sqlite:///./database.db
HOST=0.0.0.0
PORT=8000
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=5173
BACKEND_ENV
fi

# Start Backend API (port 8000)
echo "[entrypoint] Starting Backend API on port 8000..."
cd /app/charforge-gui/backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "[entrypoint] Backend PID: $BACKEND_PID"

# Start Frontend (port 5173) - only if node_modules exists
if [ -d /app/charforge-gui/frontend/node_modules ]; then
    echo "[entrypoint] Starting Frontend on port 5173..."
    cd /app/charforge-gui/frontend
    nohup npm run dev -- --host 0.0.0.0 > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "[entrypoint] Frontend PID: $FRONTEND_PID"
else
    echo "[entrypoint] Frontend node_modules not found. Run 'cd /app/charforge-gui/frontend && npm install' to enable."
fi

# Start ComfyUI (port 8188)
echo "[entrypoint] Starting ComfyUI on port 8188..."
cd /app/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 > /tmp/comfyui.log 2>&1 &
COMFYUI_PID=$!
echo "[entrypoint] ComfyUI PID: $COMFYUI_PID"

# Print welcome message
echo ""
echo "================================================="
echo "  CharForgex Docker Container"
echo "================================================="
echo ""
echo "Services running:"
echo "  - SSH:      port 22 (no password)"
echo "  - Backend:  port 8000 (API)"
echo "  - Frontend: port 5173 (GUI)"
echo "  - ComfyUI:  port 8188"
echo ""
echo "Logs:"
echo "  - Backend:  tail -f /tmp/backend.log"
echo "  - Frontend: tail -f /tmp/frontend.log"
echo "  - ComfyUI:  tail -f /tmp/comfyui.log"
echo "  - Setup:    cat /tmp/setup.log"
echo ""
if [ -f "$SETUP_MARKER" ]; then
    echo "Setup Status: COMPLETE ($(cat $SETUP_MARKER))"
else
    echo "Setup Status: NOT COMPLETE - run 'cd /app && bash setup.sh'"
fi
echo ""
echo "TRAINING:"
echo "  cd /app && python train_character.py --name \"NAME\" --input \"/path/to/image.jpg\""
echo ""
echo "INFERENCE:"
echo "  cd /app && python test_character.py --character_name \"NAME\" --prompt \"Your prompt\""
echo ""
echo "================================================="
echo "Container is ready. Keeping alive..."
echo "================================================="
echo ""

# Change to app directory
cd /app

# Keep container alive
exec sleep infinity
