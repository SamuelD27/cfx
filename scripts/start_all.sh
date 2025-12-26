#!/bin/bash
# CharForgex Comprehensive Startup Script
# ========================================
# Single entrypoint to start all services reliably
# All paths point to network volume for persistence
#
# Usage: ./start_all.sh [all|backend|frontend|comfyui|status|stop|health]

set -euo pipefail

# ============================================================
# CONFIGURATION
# ============================================================
CHARFORGE_ROOT="/app"
RUNTIME_DIR="$CHARFORGE_ROOT/runtime"
LOGS_DIR="$RUNTIME_DIR/logs"

BACKEND_PORT=8000
FRONTEND_PORT=5173
COMFYUI_PORT=8188

BACKEND_DIR="$CHARFORGE_ROOT/charforge-gui/backend"
FRONTEND_DIR="$CHARFORGE_ROOT/charforge-gui/frontend"
COMFYUI_DIR="$CHARFORGE_ROOT/ComfyUI"

# Log files
BACKEND_LOG="/tmp/backend.log"
FRONTEND_LOG="/tmp/frontend.log"
COMFYUI_LOG="/tmp/comfyui.log"

# PID tracking
PID_DIR="$RUNTIME_DIR/pids"
mkdir -p "$PID_DIR" "$LOGS_DIR"

# ============================================================
# ENVIRONMENT SETUP
# ============================================================
setup_environment() {
    echo "[startup] Setting up environment..."
    
    # Export critical paths (use /app for container disk storage)
    export HF_HOME=/app/hf_cache
    export TORCH_HOME=/app/torch_cache
    export TMPDIR=/app/runtime/tmp
    export XDG_CACHE_HOME=/app/.cache
    # Node is installed system-wide in Docker image
    
    # Load API keys from .env
    if [ -f "$CHARFORGE_ROOT/.env" ]; then
        set -a
        source "$CHARFORGE_ROOT/.env"
        set +a
    fi
    
    # Ensure symlinks exist for Docker compatibility
    if [ -d /app ] && [ ! -L /app/ComfyUI ]; then
        rm -rf /app/ComfyUI 2>/dev/null || true
        ln -sf "$COMFYUI_DIR" /app/ComfyUI 2>/dev/null || true
    fi
    if [ -d /app ] && [ ! -L /app/.env ]; then
        rm -f /app/.env 2>/dev/null || true
        ln -sf "$CHARFORGE_ROOT/.env" /app/.env 2>/dev/null || true
    fi
    
    echo "[startup] Environment configured"
}

# ============================================================
# DEPENDENCY CHECK
# ============================================================
check_dependencies() {
    echo "[startup] Checking dependencies..."
    
    local MISSING=""
    
    # Check Python deps
    python3 -c "import fastapi" 2>/dev/null || MISSING="$MISSING fastapi"
    python3 -c "import uvicorn" 2>/dev/null || MISSING="$MISSING uvicorn"
    python3 -c "import torch" 2>/dev/null || MISSING="$MISSING torch"
    python3 -c "import cv2" 2>/dev/null || MISSING="$MISSING opencv"
    python3 -c "import safetensors" 2>/dev/null || MISSING="$MISSING safetensors"
    
    if [ -n "$MISSING" ]; then
        echo "[startup] Installing missing deps:$MISSING"
        pip install fastapi uvicorn opencv-python-headless safetensors matplotlib insightface onnxruntime -q 2>/dev/null || true
    fi
    
    # Check Node (installed system-wide in Docker image)
    if ! command -v node &>/dev/null; then
        echo "[startup] WARNING: Node.js not found"
    fi
    
    echo "[startup] Dependencies OK"
}

# ============================================================
# SERVICE MANAGEMENT
# ============================================================
get_pid() {
    local service=$1
    case $service in
        backend)  pgrep -f "uvicorn app.main:app.*$BACKEND_PORT" 2>/dev/null | head -1 ;;
        frontend) pgrep -f "node.*vite.*$FRONTEND_PORT" 2>/dev/null | head -1 ;;
        comfyui)  pgrep -f "python main.py.*$COMFYUI_PORT" 2>/dev/null | head -1 ;;
    esac
}

start_backend() {
    echo "[startup] Starting Backend API on port $BACKEND_PORT..."
    
    local PID=$(get_pid backend)
    if [ -n "$PID" ]; then
        echo "[startup] Backend already running (PID: $PID)"
        return 0
    fi
    
    cd "$BACKEND_DIR"
    
    # Ensure encryption key exists
    if [ ! -f encryption.key ]; then
        python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > encryption.key
    fi
    
    # Ensure .env exists
    if [ ! -f .env ]; then
        cat > .env << BACKEND_ENV
ENABLE_AUTH=false
ALLOW_REGISTRATION=false
DEFAULT_USER_ID=1
SECRET_KEY=charforge-local-dev-key
DATABASE_URL=sqlite:///./database.db
HOST=0.0.0.0
PORT=8000
BACKEND_ENV
    fi
    
    # Start uvicorn
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT >> "$BACKEND_LOG" 2>&1 &
    
    # Wait for health
    for i in {1..20}; do
        if curl -sf http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
            PID=$(get_pid backend)
            echo "[startup] Backend started (PID: $PID)"
            return 0
        fi
        sleep 1
    done
    
    echo "[startup] ERROR: Backend failed to start"
    tail -20 "$BACKEND_LOG"
    return 1
}

start_frontend() {
    echo "[startup] Starting Frontend on port $FRONTEND_PORT..."
    
    local PID=$(get_pid frontend)
    if [ -n "$PID" ]; then
        echo "[startup] Frontend already running (PID: $PID)"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # Ensure node_modules exist
    if [ ! -d node_modules ]; then
        echo "[startup] Installing frontend dependencies..."
        npm install --silent 2>/dev/null
    fi
    
    # Start Vite
    nohup npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT >> "$FRONTEND_LOG" 2>&1 &
    
    # Wait for health
    for i in {1..30}; do
        if curl -sf http://localhost:$FRONTEND_PORT >/dev/null 2>&1; then
            PID=$(get_pid frontend)
            echo "[startup] Frontend started (PID: $PID)"
            return 0
        fi
        sleep 1
    done
    
    echo "[startup] ERROR: Frontend failed to start"
    tail -20 "$FRONTEND_LOG"
    return 1
}

start_comfyui() {
    echo "[startup] Starting ComfyUI on port $COMFYUI_PORT..."
    
    local PID=$(get_pid comfyui)
    if [ -n "$PID" ]; then
        echo "[startup] ComfyUI already running (PID: $PID)"
        return 0
    fi
    
    if [ ! -d "$COMFYUI_DIR" ] || [ ! -f "$COMFYUI_DIR/main.py" ]; then
        echo "[startup] WARNING: ComfyUI not installed at $COMFYUI_DIR"
        return 1
    fi
    
    cd "$COMFYUI_DIR"
    
    # Install ComfyUI requirements if needed
    pip install -r requirements.txt -q 2>/dev/null || true
    
    # Start ComfyUI
    nohup python main.py --listen 0.0.0.0 --port $COMFYUI_PORT >> "$COMFYUI_LOG" 2>&1 &
    
    # Wait for health
    for i in {1..60}; do
        if curl -sf http://localhost:$COMFYUI_PORT >/dev/null 2>&1; then
            PID=$(get_pid comfyui)
            echo "[startup] ComfyUI started (PID: $PID)"
            return 0
        fi
        sleep 1
    done
    
    echo "[startup] ERROR: ComfyUI failed to start (may still be loading)"
    tail -20 "$COMFYUI_LOG"
    return 1
}

stop_service() {
    local service=$1
    local PID=$(get_pid $service)
    
    if [ -n "$PID" ]; then
        echo "[startup] Stopping $service (PID: $PID)..."
        kill $PID 2>/dev/null || true
        sleep 2
        kill -9 $PID 2>/dev/null || true
    fi
}

stop_all() {
    echo "[startup] Stopping all services..."
    stop_service backend
    stop_service frontend
    stop_service comfyui
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true
    pkill -f "python main.py" 2>/dev/null || true
    echo "[startup] All services stopped"
}

show_status() {
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                  CharForgex Service Status                       ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    local BACKEND_PID=$(get_pid backend)
    local FRONTEND_PID=$(get_pid frontend)
    local COMFYUI_PID=$(get_pid comfyui)
    
    printf "%-12s %-8s %-10s %s\n" "SERVICE" "PORT" "STATUS" "PID"
    echo "────────────────────────────────────────────────────────────────────"
    
    if [ -n "$BACKEND_PID" ] && curl -sf http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
        printf "%-12s %-8s %-10s %s\n" "Backend" "$BACKEND_PORT" "✓ HEALTHY" "$BACKEND_PID"
    elif [ -n "$BACKEND_PID" ]; then
        printf "%-12s %-8s %-10s %s\n" "Backend" "$BACKEND_PORT" "⚠ RUNNING" "$BACKEND_PID"
    else
        printf "%-12s %-8s %-10s %s\n" "Backend" "$BACKEND_PORT" "✗ STOPPED" "-"
    fi
    
    if [ -n "$FRONTEND_PID" ] && curl -sf http://localhost:$FRONTEND_PORT >/dev/null 2>&1; then
        printf "%-12s %-8s %-10s %s\n" "Frontend" "$FRONTEND_PORT" "✓ HEALTHY" "$FRONTEND_PID"
    elif [ -n "$FRONTEND_PID" ]; then
        printf "%-12s %-8s %-10s %s\n" "Frontend" "$FRONTEND_PORT" "⚠ RUNNING" "$FRONTEND_PID"
    else
        printf "%-12s %-8s %-10s %s\n" "Frontend" "$FRONTEND_PORT" "✗ STOPPED" "-"
    fi
    
    if [ -n "$COMFYUI_PID" ] && curl -sf http://localhost:$COMFYUI_PORT >/dev/null 2>&1; then
        printf "%-12s %-8s %-10s %s\n" "ComfyUI" "$COMFYUI_PORT" "✓ HEALTHY" "$COMFYUI_PID"
    elif [ -n "$COMFYUI_PID" ]; then
        printf "%-12s %-8s %-10s %s\n" "ComfyUI" "$COMFYUI_PORT" "⚠ LOADING" "$COMFYUI_PID"
    else
        printf "%-12s %-8s %-10s %s\n" "ComfyUI" "$COMFYUI_PORT" "✗ STOPPED" "-"
    fi
    
    echo ""
}

health_check() {
    local ALL_OK=true
    
    curl -sf http://localhost:$BACKEND_PORT/health >/dev/null 2>&1 || ALL_OK=false
    curl -sf http://localhost:$FRONTEND_PORT >/dev/null 2>&1 || ALL_OK=false
    curl -sf http://localhost:$COMFYUI_PORT >/dev/null 2>&1 || ALL_OK=false
    
    if $ALL_OK; then
        echo "ALL_HEALTHY"
        return 0
    else
        echo "UNHEALTHY"
        return 1
    fi
}

start_all() {
    setup_environment
    check_dependencies
    
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "                 Starting CharForgex Services                       "
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    
    start_backend
    start_frontend
    start_comfyui
    
    echo ""
    show_status
}

# ============================================================
# MAIN
# ============================================================
case "${1:-all}" in
    all)      start_all ;;
    backend)  setup_environment && start_backend ;;
    frontend) setup_environment && start_frontend ;;
    comfyui)  setup_environment && start_comfyui ;;
    stop)     stop_all ;;
    restart)  stop_all && sleep 2 && start_all ;;
    status)   show_status ;;
    health)   health_check ;;
    *)
        echo "Usage: $0 [all|backend|frontend|comfyui|stop|restart|status|health]"
        exit 1
        ;;
esac
