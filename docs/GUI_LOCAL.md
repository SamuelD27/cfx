# GUI Local Setup Guide

[Back to README](../README.md)

CharForgex includes an optional web-based GUI for managing characters, training, and inference. This document covers local-only setup.

---

## Overview

The GUI consists of:
- **Frontend**: Vue 3 + TypeScript + TailwindCSS (port 5173)
- **Backend**: FastAPI + SQLite (port 8000)

**Security Note**: Authentication is **disabled by default**. The GUI is designed for local/personal use only. Do not expose to the public internet without enabling authentication.

---

## Prerequisites

- Node.js 18+
- Python 3.10+ (same as main pipeline)
- CharForgex setup completed (`bash setup.sh` run)
- API keys configured in `.env`

---

## Quick Start

```bash
cd charforge-gui
./start-dev.sh
```

This script:
1. Checks dependencies (Python, Node.js)
2. Creates Python virtual environment for backend
3. Installs backend dependencies
4. Installs frontend dependencies
5. Starts both servers

**Access**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Manual Setup

If `start-dev.sh` fails, set up manually:

### Backend

```bash
cd charforge-gui/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env (or copy from parent)
cp ../.env.example .env
# Edit .env with your API keys

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd charforge-gui/frontend

# Install dependencies
npm install

# Start frontend
npm run dev -- --host 0.0.0.0
```

---

## Configuration

### Backend Environment Variables

Create `charforge-gui/backend/.env`:

```bash
# Authentication (disabled by default)
ENABLE_AUTH=false
ALLOW_REGISTRATION=false
DEFAULT_USER_ID=1

# Security (change in production)
SECRET_KEY=your-secret-key-change-this

# Database
DATABASE_URL=sqlite:///./database.db

# Server
HOST=0.0.0.0
PORT=8000

# CharForge Integration
CHARFORGE_ROOT=../

# API Keys (same as main .env)
HF_TOKEN=your_token
HF_HOME=/path/to/cache
CIVITAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
FAL_KEY=your_key

# Training Defaults
DEFAULT_STEPS=800
DEFAULT_BATCH_SIZE=1
DEFAULT_LEARNING_RATE=8e-4
DEFAULT_TRAIN_DIM=512
DEFAULT_RANK_DIM=8

# Inference Defaults
DEFAULT_LORA_WEIGHT=0.73
DEFAULT_TEST_DIM=1024
DEFAULT_INFERENCE_STEPS=30
DEFAULT_BATCH_SIZE_INFERENCE=4
```

---

## Data Storage

| Data | Location |
|------|----------|
| Database | `charforge-gui/backend/database.db` |
| Uploaded media | `charforge-gui/backend/media/` |
| Inference results | `charforge-gui/backend/results/` |
| Character data | `./scratch/` (shared with CLI) |

---

## Features

### Character Management

- Create new characters from uploaded images
- View training status and progress
- Manage existing characters

### Training

- Configure training parameters via UI
- Monitor real-time progress (WebSocket)
- View training logs

### Inference

- Select trained characters
- Configure generation settings
- Generate and download images

### Settings

- Configure API keys via UI
- Test environment configuration
- View system status

---

## Authentication (Optional)

To enable authentication for multi-user or remote access:

```bash
# In backend/.env
ENABLE_AUTH=true
ALLOW_REGISTRATION=true
```

When enabled:
- Users must register/login
- Separate user data isolation
- JWT-based authentication

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using ports
lsof -i :5173
lsof -i :8000

# Kill processes
kill -9 <PID>
```

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.10+

# Check venv is activated
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend Won't Start

```bash
# Check Node version
node --version  # Should be 18+

# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Database Issues

```bash
# Reset database
rm charforge-gui/backend/database.db
# Restart backend (will recreate)
```

### Can't Find Characters

The GUI looks for characters in `./scratch/` relative to `CHARFORGE_ROOT`.

```bash
# Verify CHARFORGE_ROOT in backend/.env
# Should point to the main CharForgex directory

# Check characters exist
ls ./scratch/
```

---

## Integration with CLI

The GUI calls the same Python scripts as the CLI:
- Training: `train_character.py`
- Inference: `test_character.py`

Character data in `./scratch/` is shared between GUI and CLI. You can:
- Train via CLI, inference via GUI
- Train via GUI, inference via CLI
- Mix freely

---

## Security Warnings

1. **Authentication disabled by default**: Anyone with network access can use the GUI
2. **API keys stored in .env**: Protect this file
3. **SQLite database**: Not suitable for high-concurrency production use
4. **No HTTPS**: Traffic is unencrypted on local network

**For local-only use**: These are acceptable tradeoffs.

**For remote access**: Enable authentication, use HTTPS, consider firewall rules.

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md)
