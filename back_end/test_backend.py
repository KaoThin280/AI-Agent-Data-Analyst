#!/usr/bin/env python3
"""
Test script for the BI Platform backend structured workflow.

Prerequisites:
  - Server running at http://localhost:8000
  - A sample CSV file named 'sample_timeseries.csv' in the current directory
    (or adjust the path in the script)
  - A .env file with BACKEND_SECRET_TOKEN set in the same directory

Usage:
  python test_backend.py
"""

import os
import sys
import json
import time
import re
import requests
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000"


def load_api_key() -> str:
    """Read BACKEND_SECRET_TOKEN from .env file in the current directory."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.is_file():
        print("  ❌ .env file not found in script directory.")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("BACKEND_SECRET_TOKEN"):
                # Handle BACKEND_SECRET_TOKEN=value or BACKEND_SECRET_TOKEN="value"
                match = re.match(r'^BACKEND_SECRET_TOKEN\s*=\s*["\']?(.*?)["\']?\s*$', line)
                if match:
                    return match.group(1)
    print("  ❌ BACKEND_SECRET_TOKEN not found in .env")
    sys.exit(1)


HEADERS = {}

def setup():
    global HEADERS
    api_key = load_api_key()
    HEADERS = {"X-API-Key": api_key}
    print(f"  🔑 API key loaded from .env")


# ── Logging helper ──────────────────────────────────────────────────────

LOG_FILE = Path(__file__).parent / "test_response.txt"

def log(msg: str = "", end="\n"):
    """Print to console and append to test_response.txt."""
    print(msg, end=end)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + ("\n" if end == "\n" else ""))


def log_separator(title: str):
    sep = "=" * 60
    log(f"\n{sep}")
    log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – {title}")
    log(sep)


# ── API helpers ─────────────────────────────────────────────────────────

def upload_file(file_path: str) -> dict:
    """Upload a file and return the response JSON."""
    url = f"{BASE_URL}/upload"
    if not os.path.isfile(file_path):
        log(f"  ❌ File not found: {file_path}")
        sys.exit(1)
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "text/csv")}
        resp = requests.post(url, files=files, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def chat_query(query: str) -> dict:
    """Send a chat query and return the response JSON."""
    url = f"{BASE_URL}/chat"
    params = {"query": query}
    resp = requests.post(url, params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def download_file(url_path: str, local_name: str) -> bool:
    """Download a static file from the server (if publicly accessible)."""
    url = f"{BASE_URL}{url_path}"
    try:
        resp = requests.get(url, stream=True, timeout=5)
        if resp.status_code == 200:
            with open(local_name, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception:
        pass
    return False


# ── Evaluation ──────────────────────────────────────────────────────────

def evaluate(results: dict):
    """Print an evaluation summary."""
    log()
    log("EVALUATION REPORT")
    log("-" * 40)
    for key, val in results.items():
        icon = "✅" if val else "❌"
        log(f"  {icon}  {key}")
    log("-" * 40)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    # Clear previous log
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    setup()
    log_separator("START TEST SUITE")
    log(f"  Server: {BASE_URL}")
    log(f"  File: sample_timeseries.csv")

    # ── 1. Upload file ──────────────────────────────────────────────
    log_separator("1. UPLOAD FILE")
    try:
        upload_resp = upload_file("sample_timeseries.csv")
        log(f"  Status: {upload_resp.get('status')}")
        log(f"  File name: {upload_resp.get('file_name')}")
        log(f"  Rows: {upload_resp.get('num_rows')}, Columns: {upload_resp.get('num_columns')}")
        ai_analysis = upload_resp.get("ai_analysis", "")
        log(f"\n  AI Analysis:")
        log(f"  {ai_analysis}")
        log()
        data_context = upload_resp.get("data_context", {})
        # Log columns for reference
        cols = data_context.get("columns", {})
        log(f"  Columns detected:")
        for col_name, col_info in cols.items():
            log(f"    - {col_name}: {col_info.get('dtype', 'unknown')}")
        upload_ok = True
    except Exception as e:
        log(f"  ❌ Upload failed: {e}")
        upload_ok = False

    # ── 2. Query 1: chart ───────────────────────────────────────────
    log_separator("2. QUERY 1 – 'draw revenue by months chart'")
    try:
        q1_resp = chat_query("draw revenue by months chart")
        user_resp_1 = q1_resp.get("user_response", "")
        code_1 = q1_resp.get("code_executed")
        artifacts_1 = q1_resp.get("artifacts_created", [])
        retries_1 = q1_resp.get("retries_used", 0)

        log(f"  Retries used: {retries_1}")
        log(f"\n  User response:")
        log(f"  {user_resp_1}")
        log()
        if code_1:
            log(f"  Code executed (length: {len(code_1)} chars):")
            log(f"  {code_1}")
            log()
        if artifacts_1:
            log(f"  Artifacts created: {artifacts_1}")
        else:
            log(f"  Artifacts created: (none)")
        q1_ok = True
    except Exception as e:
        log(f"  ❌ Query 1 failed: {e}")
        q1_ok = False
        artifacts_1 = []

    # ── 3. Download artifacts ───────────────────────────────────────
    if artifacts_1:
        log_separator("3. DOWNLOAD ARTIFACTS")
        for art in artifacts_1:
            # Adjust path as needed; typical endpoints might be:
            #   /static/{art}
            #   /temp_data/{art}
            for prefix in ["/temp_data/", "/static/", "/download/"]:
                path = f"{prefix}{art}"
                local = f"downloaded_{art}"
                if download_file(path, local):
                    log(f"  ✅ Downloaded '{art}' as '{local}'")
                    break
            else:
                log(f"  ⚠️  Could not download '{art}' – check server static file config")

    # ── 4. Query 2: highest revenue month ───────────────────────────
    log_separator("4. QUERY 2 – 'what's the month got the highest revenue?'")
    try:
        q2_resp = chat_query("what's the month got the highest revenue?")
        user_resp_2 = q2_resp.get("user_response", "")
        code_2 = q2_resp.get("code_executed")
        artifacts_2 = q2_resp.get("artifacts_created", [])
        retries_2 = q2_resp.get("retries_used", 0)

        log(f"  Retries used: {retries_2}")
        log(f"\n  User response:")
        log(f"  {user_resp_2}")
        log()
        if code_2:
            log(f"  Code executed (length: {len(code_2)} chars):")
            log(f"  {code_2}")
            log()
        if artifacts_2:
            log(f"  Artifacts created: {artifacts_2}")
        q2_ok = True
    except Exception as e:
        log(f"  ❌ Query 2 failed: {e}")
        q2_ok = False

    # ── 5. Evaluation ───────────────────────────────────────────────
    log_separator("5. EVALUATION")
    evaluate({
        "File upload succeeded": upload_ok,
        "Chart query returned response": q1_ok,
        "Highest revenue month answered": q2_ok,
    })

    log()
    log_separator("TEST SUITE COMPLETED")
    log(f"  Full log written to: {LOG_FILE.resolve()}")
    log()


if __name__ == "__main__":
    main()