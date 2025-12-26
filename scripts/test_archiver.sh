#!/bin/bash
# CharForgex Test Archiver
# Creates timestamped test run folders with all logs and environment info
# Usage: ./test_archiver.sh <test_name> [start|stop|snapshot]

set -e

RUNTIME_DIR="/app/runtime"
ARCHIVES_DIR="$RUNTIME_DIR/archives"
LOGS_DIR="$RUNTIME_DIR/logs"

# Ensure directories exist
mkdir -p "$ARCHIVES_DIR" "$LOGS_DIR"

TEST_NAME="${1:-manual_test}"
ACTION="${2:-snapshot}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="$ARCHIVES_DIR/${TIMESTAMP}_${TEST_NAME}"

create_archive() {
    mkdir -p "$ARCHIVE_DIR"
    echo "Creating test archive: $ARCHIVE_DIR"
    
    # Environment snapshot
    echo "=== Environment Snapshot ===" > "$ARCHIVE_DIR/env_snapshot.txt"
    echo "Timestamp: $(date -Iseconds)" >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "Hostname: $(hostname)" >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Git Commit:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    cd /app && git log -1 --format="%H %s" >> "$ARCHIVE_DIR/env_snapshot.txt" 2>/dev/null || echo "N/A" >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Python Version:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    python3 --version >> "$ARCHIVE_DIR/env_snapshot.txt" 2>/dev/null
    
    echo "Node Version:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    node --version >> "$ARCHIVE_DIR/env_snapshot.txt" 2>/dev/null || echo "N/A" >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Key Environment Variables:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    env | grep -E "^(HF_|TORCH_|CHARFORGE_|BACKEND_|FRONTEND_|COMFYUI_|CUDA|PATH)" | sort >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Listening Ports:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    netstat -tlnp 2>/dev/null | grep -E "(8000|5173|8188)" >> "$ARCHIVE_DIR/env_snapshot.txt" || ss -tlnp 2>/dev/null | grep -E "(8000|5173|8188)" >> "$ARCHIVE_DIR/env_snapshot.txt" || echo "N/A" >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Running Processes:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    ps aux | grep -E "(python|node|uvicorn)" | grep -v grep >> "$ARCHIVE_DIR/env_snapshot.txt"
    echo "" >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    echo "Disk Usage:" >> "$ARCHIVE_DIR/env_snapshot.txt"
    df -h /app >> "$ARCHIVE_DIR/env_snapshot.txt"
    
    # Capture current logs
    cp /tmp/backend.log "$ARCHIVE_DIR/backend.log" 2>/dev/null || touch "$ARCHIVE_DIR/backend.log"
    cp /tmp/frontend.log "$ARCHIVE_DIR/frontend.log" 2>/dev/null || touch "$ARCHIVE_DIR/frontend.log"
    cp /tmp/comfyui.log "$ARCHIVE_DIR/comfyui.log" 2>/dev/null || touch "$ARCHIVE_DIR/comfyui.log"
    
    # Dependency versions
    echo "=== Python Dependencies ===" > "$ARCHIVE_DIR/dependencies.txt"
    pip list 2>/dev/null | head -50 >> "$ARCHIVE_DIR/dependencies.txt"
    
    echo "" >> "$ARCHIVE_DIR/dependencies.txt"
    echo "=== Node Dependencies ===" >> "$ARCHIVE_DIR/dependencies.txt"
    cd /app/charforge-gui/frontend && npm list --depth=0 2>/dev/null | head -30 >> "$ARCHIVE_DIR/dependencies.txt" || echo "N/A" >> "$ARCHIVE_DIR/dependencies.txt"
    
    echo "$ARCHIVE_DIR"
}

start_logging() {
    create_archive
    
    # Start log tailing in background
    echo "Starting log capture..."
    tail -f /tmp/backend.log >> "$ARCHIVE_DIR/backend.log" 2>/dev/null &
    echo $! > "$ARCHIVE_DIR/.backend_tail_pid"
    
    tail -f /tmp/frontend.log >> "$ARCHIVE_DIR/frontend.log" 2>/dev/null &
    echo $! > "$ARCHIVE_DIR/.frontend_tail_pid"
    
    tail -f /tmp/comfyui.log >> "$ARCHIVE_DIR/comfyui.log" 2>/dev/null &
    echo $! > "$ARCHIVE_DIR/.comfyui_tail_pid"
    
    echo "$ARCHIVE_DIR" > /tmp/current_test_archive
    echo "Logging started. Archive: $ARCHIVE_DIR"
}

stop_logging() {
    if [ -f /tmp/current_test_archive ]; then
        ARCHIVE_DIR=$(cat /tmp/current_test_archive)
        
        # Kill tail processes
        [ -f "$ARCHIVE_DIR/.backend_tail_pid" ] && kill $(cat "$ARCHIVE_DIR/.backend_tail_pid") 2>/dev/null
        [ -f "$ARCHIVE_DIR/.frontend_tail_pid" ] && kill $(cat "$ARCHIVE_DIR/.frontend_tail_pid") 2>/dev/null
        [ -f "$ARCHIVE_DIR/.comfyui_tail_pid" ] && kill $(cat "$ARCHIVE_DIR/.comfyui_tail_pid") 2>/dev/null
        
        # Clean up pid files
        rm -f "$ARCHIVE_DIR"/.*_tail_pid
        rm -f /tmp/current_test_archive
        
        echo "Logging stopped. Archive saved: $ARCHIVE_DIR"
        ls -la "$ARCHIVE_DIR"
    else
        echo "No active test session found"
    fi
}

case "$ACTION" in
    start)
        start_logging
        ;;
    stop)
        stop_logging
        ;;
    snapshot)
        create_archive
        ;;
    *)
        echo "Usage: $0 <test_name> [start|stop|snapshot]"
        exit 1
        ;;
esac
