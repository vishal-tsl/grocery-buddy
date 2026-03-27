#!/usr/bin/env python3
"""
Minimal release check: backend /health and optional parse-list probe.
Usage:
  python scripts/release_smoke.py
  python scripts/release_smoke.py --base-url https://your-api.example.com
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="Release smoke test for grocery API")
    p.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API origin without trailing slash",
    )
    args = p.parse_args()
    base = args.base_url.rstrip("/")

    # Health
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=15) as r:
            body = json.loads(r.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"FAIL health: {e}")
        return 1
    print(f"OK health: {body}")

    # Parse-list minimal (non-recipe)
    payload = json.dumps({"text": "eggs, milk"}).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/parse-list",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"FAIL parse-list HTTP {e.code}: {e.read().decode()[:500]}")
        return 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"FAIL parse-list: {e}")
        return 1

    items = data.get("items") or []
    if not isinstance(items, list):
        print("FAIL parse-list: items not a list")
        return 1
    print(f"OK parse-list: {len(items)} item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
