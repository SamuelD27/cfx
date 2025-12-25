#!/usr/bin/env python3
"""
CharForgex API Smoke Test
=========================
Tests all critical backend endpoints used by the GUI.
"""

import sys
import json
import time
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
RESULTS = []

def test(name, method, endpoint, expected_status=200, data=None, files=None):
    """Run a single API test"""
    url = f"{BASE_URL}{endpoint}"
    start = time.time()
    
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        elif method == "POST":
            if files:
                resp = requests.post(url, files=files, timeout=30)
            elif data:
                resp = requests.post(url, json=data, timeout=30)
            else:
                resp = requests.post(url, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=10)
        else:
            resp = requests.request(method, url, json=data, timeout=10)
        
        elapsed = (time.time() - start) * 1000
        
        passed = resp.status_code == expected_status
        result = {
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "status": resp.status_code,
            "expected": expected_status,
            "passed": passed,
            "elapsed_ms": round(elapsed, 1),
            "response_preview": str(resp.text)[:200] if not passed else None
        }
        
    except Exception as e:
        result = {
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "status": "ERROR",
            "expected": expected_status,
            "passed": False,
            "elapsed_ms": 0,
            "error": str(e)
        }
    
    RESULTS.append(result)
    status_icon = "✓" if result["passed"] else "✗"
    print(f"  {status_icon} {name}: {result['status']} ({result['elapsed_ms']}ms)")
    return result

def run_tests():
    print("=" * 60)
    print("CharForgex API Smoke Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)
    print()
    
    # =========================================================
    # HEALTH & CONFIG
    # =========================================================
    print("[1] Health & Configuration")
    test("Health Check", "GET", "/health")
    test("Auth Config", "GET", "/api/auth/config")
    test("OpenAPI Spec", "GET", "/openapi.json")
    
    # =========================================================
    # TRAINING (GUI PRIMARY FLOW)
    # =========================================================
    print("\n[2] Training Endpoints (GUI Primary Flow)")
    test("List Characters", "GET", "/api/training/characters")
    
    # Create a test character
    create_result = test(
        "Create Character", 
        "POST", 
        "/api/training/characters",
        expected_status=200,
        data={"name": f"smoke_test_{int(time.time())}"}
    )
    
    # Get character ID for further tests
    char_id = None
    if create_result["passed"]:
        try:
            resp = requests.get(f"{BASE_URL}/api/training/characters")
            chars = resp.json()
            if chars:
                char_id = chars[-1]["id"]
        except:
            pass
    
    if char_id:
        test("Get Character", "GET", f"/api/training/characters/{char_id}")
        test("Get Training Status", "GET", f"/api/training/characters/{char_id}/training")
    
    # =========================================================
    # INFERENCE
    # =========================================================
    print("\n[3] Inference Endpoints")
    test("List Jobs", "GET", "/api/inference/jobs")
    test("Available Characters", "GET", "/api/inference/available-characters")
    
    # =========================================================
    # MEDIA
    # =========================================================
    print("\n[4] Media Endpoints")
    test("List Files", "GET", "/api/media/files")
    
    # =========================================================
    # SETTINGS
    # =========================================================
    print("\n[5] Settings Endpoints")
    test("Get Environment", "GET", "/api/settings/environment")
    test("List Settings", "GET", "/api/settings/settings")
    
    # =========================================================
    # MODELS
    # =========================================================
    print("\n[6] Models Endpoints")
    test("List Models", "GET", "/api/models")
    test("List Trainers", "GET", "/api/models/trainers")
    
    # =========================================================
    # ERROR HANDLING
    # =========================================================
    print("\n[7] Error Handling")
    test("404 on Invalid Route", "GET", "/api/nonexistent", expected_status=404)
    test("Invalid Character ID", "GET", "/api/training/characters/99999", expected_status=404)
    
    # =========================================================
    # SUMMARY
    # =========================================================
    print("\n" + "=" * 60)
    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    
    print(f"RESULTS: {passed}/{total} passed")
    
    failed = [r for r in RESULTS if not r["passed"]]
    if failed:
        print("\nFailed tests:")
        for r in failed:
            print(f"  ✗ {r['name']}: got {r['status']}, expected {r['expected']}")
            if r.get("response_preview"):
                print(f"    Response: {r['response_preview']}")
            if r.get("error"):
                print(f"    Error: {r['error']}")
    
    print("=" * 60)
    
    # Return exit code
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(run_tests())
