"""Read product image text using Agnes-2.0-flash vision LLM.

read --image <url> [--download <local_path>]

Reads all Chinese/Vietnamese/English text from a product image, translates
Chinese to Vietnamese, and extracts weight/dimensions.

Outputs JSON with:
  - "text_blocks": list of {chinese, vietnamese} for each text region
  - "weight_kg": extracted weight in kg or null
  - "dimensions": {l, w, h} in cm or null
  - "full_vietnamese": a complete Vietnamese text to pass to image gen
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
TIMEOUT = 180

SYSTEM_PROMPT = """You are a product image text analyst. Your job is to:

1. Read ALL text visible in the product image — every label, title, subtitle, spec, material, size, weight.
2. For each piece of Chinese text, translate it to natural Vietnamese.
3. Extract product weight if mentioned (convert to kg: g÷1000, lb×0.4536, 斤×0.5).
4. Extract product dimensions (length × width × height, in cm).
5. Return a complete Vietnamese description that can be used as the text overlay on the image.

Output ONLY valid JSON:
{
  "text_blocks": [
    {"chinese": "原中文", "vietnamese": "Bản dịch tiếng Việt"}
  ],
  "weight_kg": <number or null>,
  "dimensions": {"l": <number or null>, "w": <number or null>, "h": <number or null>},
  "full_vietnamese": "All translated Vietnamese text combined, ready to put on image"
}"""


def get_api_key() -> str:
    for name in ("AGNES_API_KEY", "AGNES_API_TOKEN", "APIHUB_AGNES_API_KEY"):
        v = os.environ.get(name)
        if v:
            return v.strip()
    here = Path(__file__).resolve().parent.parent
    keyfile = here / "assets" / "agnes_key.txt"
    if keyfile.is_file():
        return keyfile.read_text(encoding="utf-8").strip()
    raise SystemExit("Missing API key. Set AGNES_API_KEY env var.")


def read_image(image_url: str) -> dict:
    key = get_api_key()
    # If it's a local file, convert to data URI
    payload = {
        "model": "agnes-2.0-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Read and analyze this product image. Extract all text, translate Chinese to Vietnamese, extract weight and dimensions."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]},
        ],
        "max_tokens": 4096,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    # Parse JSON from the response
    # Try to find JSON block
    import re
    json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    # If no markdown block, try parsing entire content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Return raw content wrapped
        return {"raw_content": content, "text_blocks": [], "weight_kg": None, "dimensions": None, "full_vietnamese": ""}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read")
    r.add_argument("--image", required=True, help="Image URL or local file path")
    args = ap.parse_args(argv)

    url = args.image
    # Check if local file
    p = Path(url)
    if p.is_file():
        import base64
        raw = p.read_bytes()
        suffix = p.suffix.lower()
        mime = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif",
        }.get(suffix, "image/jpeg")
        url = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    elif url.startswith(("http://", "https://")):
        pass  # Keep as-is
    else:
        import base64
        try:
            raw = Path(url).read_bytes()
            url = f"data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
        except Exception:
            pass

    result = read_image(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
