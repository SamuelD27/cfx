#!/usr/bin/env python3
"""
Diagnostic script to verify environment variable loading
Usage: python scripts/diagnostics/check_env_loading.py
"""

import os
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

print("=" * 80)
print("ENVIRONMENT VARIABLE LOADING DIAGNOSTIC")
print("=" * 80)

# Check 1: Current working directory
print(f"\n1. Current working directory: {os.getcwd()}")

# Check 2: Script location
print(f"2. This script location: {Path(__file__).absolute()}")
print(f"3. Repo root (calculated): {repo_root.absolute()}")

# Check 3: Check if .env exists
env_file = repo_root / ".env"
print(f"\n4. .env file location: {env_file}")
print(f"5. .env file exists: {env_file.exists()}")

if env_file.exists():
    print(f"6. .env file size: {env_file.stat().st_size} bytes")
    print(f"7. .env file readable: {os.access(env_file, os.R_OK)}")

    # Read and parse .env file
    print("\n8. Keys in .env file:")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key = line.split("=")[0]
                print(f"   - {key}")

# Check 4: Load dotenv and check environment
print("\n" + "=" * 80)
print("BEFORE load_dotenv():")
print("=" * 80)
print(f"FAL_KEY in environment: {('FAL_KEY' in os.environ)}")
print(f"FAL_KEY value: {'SET' if os.environ.get('FAL_KEY') else 'NOT SET'}")

from dotenv import load_dotenv

# Try loading with explicit path
print("\n" + "=" * 80)
print("LOADING .env with explicit path...")
print("=" * 80)
result = load_dotenv(env_file, verbose=True, override=True)
print(f"load_dotenv() returned: {result}")

print("\n" + "=" * 80)
print("AFTER load_dotenv():")
print("=" * 80)
print(f"FAL_KEY in environment: {('FAL_KEY' in os.environ)}")
fal_key = os.environ.get("FAL_KEY", "")
if fal_key:
    print(f"FAL_KEY value: {'*' * 10}{fal_key[-10:]if len(fal_key) > 10 else fal_key}")
    print(f"FAL_KEY length: {len(fal_key)}")
else:
    print("FAL_KEY value: NOT SET")

# Check 5: Test fal_client configuration
print("\n" + "=" * 80)
print("FAL_CLIENT CONFIGURATION:")
print("=" * 80)

try:
    import fal_client
    print(f"fal_client module location: {fal_client.__file__}")

    # Try to trigger auth to see error
    try:
        from fal_client.auth import get_default_credentials
        creds = get_default_credentials()
        print(f"✓ Credentials found: {type(creds)}")
    except Exception as e:
        print(f"✗ Credential error: {type(e).__name__}: {e}")

except ImportError as e:
    print(f"✗ Could not import fal_client: {e}")

# Check 6: Other critical environment variables
print("\n" + "=" * 80)
print("OTHER CRITICAL ENVIRONMENT VARIABLES:")
print("=" * 80)
critical_vars = ["HF_TOKEN", "GOOGLE_API_KEY", "CIVITAI_API_KEY", "HF_HOME"]
for var in critical_vars:
    value = os.environ.get(var, "")
    if value:
        print(f"✓ {var}: SET (length={len(value)})")
    else:
        print(f"✗ {var}: NOT SET")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
