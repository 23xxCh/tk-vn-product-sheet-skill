"""Parallel batch image processor — fast mode.

Usage:
  python scripts/batch_process.py "<xlsx>" [--doubao-key KEY] [--hfsy-key KEY] [--agnes-key KEY]

Pipeline:
  1. prepare (deterministic: brand/stock/SKU/video)
  2. Vision pre-screen all unique images (10 parallel) → classify clean/brand/text/promo
  3. Batch image gen for brand/text only (5 parallel, Doubao→hfsyapi fallback)
  4. Share main/sub URLs to all variant rows
  5. finalize (write all results)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_pipeline  # noqa: E402
from run_pipeline import prepare as rp_prepare, finalize as rp_finalize


# ── API call helpers ──────────────────────────────────────


def vision_classify(url: str, agnes_key: str, timeout: int = 30) -> str:
    """Classify a single image by URL via Agnes 2.0 flash vision.
    Returns 'clean' | 'brand' | 'text' | 'promo' | 'unknown'.
    No local download — sends URL directly.
    """
    try:
        resp = requests.post(
            "https://apihub.agnes-ai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {agnes_key}"},
            json={
                "model": "agnes-2.0-flash",
                "messages": [
                    {"role": "system",
                     "content": "Classify this product image. Output ONE word only: clean (no brand/text/watermark), brand (has brand logo), text (has Chinese text), promo (coupon/after-sales banner)."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Classify this image."},
                        {"type": "image_url", "image_url": {"url": url}}
                    ]}
                ],
                "max_tokens": 10,
            },
            timeout=timeout,
        )
        label = resp.json()["choices"][0]["message"]["content"].strip().lower()
        if label in ("clean", "brand", "text", "promo"):
            return label
    except Exception:
        pass
    return "unknown"


def doubao_gen(url: str, key: str, size: str = "2K", timeout: int = 120) -> str | None:
    """Generate cleaned image via Doubao Seedream 5.0. Returns URL or None."""
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "doubao-seedream-5-0-260128",
                "prompt": "Remove brand names, logos and watermarks from the image, and translate all text to Vietnamese.",
                "image": url,
                "response_format": "url",
                "size": size,
                "watermark": False,
            },
            timeout=timeout,
        )
        return resp.json()["data"][0]["url"]
    except Exception:
        return None


def hfsyapi_gen(url: str, key: str, timeout: int = 180) -> str | None:
    """Fallback: generate via GPT-Image-2 / hfsyapi. Returns URL or None."""
    try:
        ref = url
        # If gw.alicdn, download → base64
        if "gw.alicdn" in url:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                import base64
                ref = f"data:image/jpeg;base64,{base64.b64encode(r.content).decode()}"
        resp = requests.post(
            "https://www.hfsyapi.cn/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "User-Agent": "curl/7.68.0"},
            json={
                "model": "gpt-image-2",
                "prompt": "Remove brand names, logos and watermarks from the image, and translate all text to Vietnamese.",
                "reference_images": [ref],
                "size": "1024x1024",
                "n": 1,
                "response_format": "url",
            },
            timeout=timeout,
        )
        return resp.json()["data"][0]["url"]
    except Exception:
        return None


# ── Main pipeline ─────────────────────────────────────────


def auto_process(xlsx_path: str, ark_key: str, hfsy_key: str, agnes_key: str,
                 work_path: str | None = None) -> dict[str, Any]:
    xlsx = Path(xlsx_path).resolve()
    work = Path(work_path or xlsx.with_name("work_auto.json")).resolve()

    # Step 1: prepare (fast, <1s)
    print("🔧 [1/5] Prepare (deterministic transforms)...", flush=True)
    rp_prepare(str(xlsx), str(work))
    w = json.loads(work.read_text(encoding="utf-8"))

    # Collect unique image URLs
    unique_urls: dict[str, dict] = {}
    for row in w["rows"]:
        for img in row["images"]:
            url = img["orig"]
            if url and url not in unique_urls:
                unique_urls[url] = img

    all_urls = list(unique_urls.keys())
    print(f"   Found {len(all_urls)} unique image URLs across {len(w['rows'])} rows", flush=True)

    # Step 2: Vision pre-screen (parallel, ~2min for 120 images)
    print("👁️ [2/5] Vision pre-screening (classifying images)...", flush=True)
    classifications: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        fut = {ex.submit(vision_classify, url, agnes_key): url for url in all_urls}
        for f in as_completed(fut):
            url = fut[f]
            classifications[url] = f.result()
    cats: dict[str, int] = {}
    for c in classifications.values():
        cats[c] = cats.get(c, 0) + 1
    print(f"   clean={cats.get('clean',0)} brand={cats.get('brand',0)} text={cats.get('text',0)} promo={cats.get('promo',0)} unknown={cats.get('unknown',0)}", flush=True)

    # Step 3: Delete promo images from work.json
    for row in w["rows"]:
        for img in row["images"]:
            cls = classifications.get(img["orig"], "unknown")
            if cls == "promo":
                img["decision"] = "delete"

    # Step 4: Generate only for brand/text (parallel, 5 concurrent)
    to_gen = [u for u in all_urls if classifications.get(u) in ("brand", "text")]
    print(f"🖼️ [3/5] Generating cleaned images for {len(to_gen)} images (5 parallel)...", flush=True)
    gen_results: dict[str, str | None] = {}

    def gen_one(url: str) -> tuple[str, str | None]:
        # Try Doubao first
        if ark_key:
            result = doubao_gen(url, ark_key)
            if result:
                return url, result
        # Fallback to hfsyapi
        if hfsy_key:
            result = hfsyapi_gen(url, hfsy_key)
            if result:
                return url, result
        return url, None

    with ThreadPoolExecutor(max_workers=5) as ex:
        fut = {ex.submit(gen_one, url): url for url in to_gen}
        for f in as_completed(fut):
            url = fut[f]
            _, new_url = f.result()
            gen_results[url] = new_url

    gen_ok = sum(1 for v in gen_results.values() if v)
    gen_fail = sum(1 for v in gen_results.values() if not v)
    print(f"   Generated: {gen_ok} OK, {gen_fail} failed/kept original", flush=True)

    # Apply results to work.json
    for row in w["rows"]:
        for img in row["images"]:
            url = img["orig"]
            cls = classifications.get(url, "unknown")
            if cls == "promo":
                continue  # already set to delete
            new_url = gen_results.get(url) if cls in ("brand", "text") else None
            if new_url:
                img["decision"] = "regen"
                img["new_url"] = new_url
            else:
                img["decision"] = "keep"
                img["new_url"] = ""

    # Step 4: Share main/sub URLs to variant rows
    # (Built into run_pipeline.finalize - it reads from work.json which
    #  already has results applied)

    # Save work.json with results
    work.write_text(json.dumps(w, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   Saved results to {work}", flush=True)

    # Step 5: Finalize
    print("📝 [4/5] Finalize (writing sheet)...", flush=True)
    rp_finalize(str(xlsx), str(work), str(xlsx))
    print("✅ [5/5] Done!", flush=True)

    return {
        "rows": len(w["rows"]),
        "unique_images": len(all_urls),
        "classifications": cats,
        "generated_ok": gen_ok,
        "generated_fail": gen_fail,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Auto batch process TikTok Vietnam product sheet")
    ap.add_argument("xlsx", help="Path to xlsx file")
    ap.add_argument("--doubao-key", default=os.environ.get("ARK_API_KEY", ""),
                    help="Doubao Seedream API key (env: ARK_API_KEY)")
    ap.add_argument("--hfsy-key", default=os.environ.get("HFSY_API_KEY", ""),
                    help="hfsyapi GPT-Image-2 key (env: HFSY_API_KEY)")
    ap.add_argument("--agnes-key", default=os.environ.get("AGNES_API_KEY", ""),
                    help="Agnes vision API key (env: AGNES_API_KEY)")
    ap.add_argument("--work", default=None, help="Work JSON path (default: xlsx_dir/work_auto.json)")
    args = ap.parse_args(argv)

    print("╔══════════════════════════════════════╗", flush=True)
    print("║  TK-VN Product Sheet Auto Processor  ║", flush=True)
    print("╚══════════════════════════════════════╝", flush=True)
    print(f"Input: {args.xlsx}", flush=True)
    print(f"Doubao: {'✅' if args.doubao_key else '❌'}  hfsyapi: {'✅' if args.hfsy_key else '❌'}  Vision: {'✅' if args.agnes_key else '❌'}", flush=True)
    print("", flush=True)

    report = auto_process(args.xlsx, args.doubao_key, args.hfsy_key, args.agnes_key, args.work)
    print("", flush=True)
    print("═══ Summary ═══", flush=True)
    for k, v in report.items():
        print(f"  {k}: {v}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
