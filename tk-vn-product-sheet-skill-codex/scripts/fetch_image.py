"""Download a product image URL to a local file so the agent can Read it visually.

fetch <url> <outpath>

Normalizes protocol-relative URLs first. Prints the saved path on success.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


def normalize_url(url: str) -> str:
    u = url.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://"):
        return "https://" + u[len("http://"):]
    return u


def fetch(url: str, outpath: str) -> int:
    url = normalize_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"__FAIL__ {e}")
        return 1
    Path(outpath).write_bytes(data)
    print(outpath)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: fetch_image.py <url> <outpath>")
        sys.exit(2)
    sys.exit(fetch(sys.argv[1], sys.argv[2]))
