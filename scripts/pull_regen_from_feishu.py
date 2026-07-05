"""Pull regenerated image URLs from a Feishu Bitable back into work.json.

Reads the "附件链接" (source URL) and "图片转链接" (new URL) fields from
a Feishu Base table, matches them against work.json's regen images by
original URL, and fills in the new_url field.

After pulling, run `tkvn.py finalize` to write the results into the xlsx.

Usage:
  python scripts/pull_regen_from_feishu.py <work.json> --base-token X --table-id Y
  python scripts/pull_regen_from_feishu.py <work.json> --base-token X --table-id Y \
      --source-field "附件链接" --new-field "图片转链接"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _extract_url(value) -> str:
    """Extract a clean URL from a Feishu cell value.
    Handles markdown links [text](url), plain URLs, and None."""
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    s = value.strip()
    # Markdown link: [text](url)
    m = re.search(r'\]\((https?://[^\s)]+)\)', s)
    if m:
        return m.group(1)
    # Plain URL
    if s.startswith(("http://", "https://")):
        return s
    return ""


def fetch_records(base_token: str, table_id: str,
                  source_field: str, new_field: str,
                  as_identity: str = "user") -> dict[str, str]:
    """Fetch all records, return {source_url: new_url} mapping."""
    lark_cli = shutil.which("lark-cli") or "lark-cli"
    cmd = [
        lark_cli, "base", "+record-search",
        "--base-token", base_token,
        "--table-id", table_id,
        "--as", as_identity,
        "--keyword", "http",
        "--search-field", source_field,
        "--field-id", source_field,
        "--field-id", new_field,
        "--limit", "200",
        "--format", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        try:
            err = json.loads(result.stderr or result.stdout)
        except json.JSONDecodeError:
            err = {"raw": (result.stderr or result.stdout)[:500]}
        raise RuntimeError(f"lark-cli failed: {err}")

    data = json.loads(result.stdout)
    d = data.get("data", {})
    rids = d.get("record_id_list", [])
    rows = d.get("data", [])
    fields = d.get("fields", [])

    # Find column indices
    try:
        src_idx = fields.index(source_field)
    except ValueError:
        src_idx = 0
    try:
        new_idx = fields.index(new_field)
    except ValueError:
        new_idx = 1 if len(fields) > 1 else 0

    mapping: dict[str, str] = {}
    for rid, row in zip(rids, rows):
        if not row or len(row) <= max(src_idx, new_idx):
            continue
        src_url = _extract_url(row[src_idx])
        new_url = _extract_url(row[new_idx])
        if src_url and new_url:
            mapping[src_url] = new_url
    return mapping


def update_work_json(work_path: str, url_mapping: dict[str, str]) -> dict:
    """Update work.json's new_url fields based on the mapping.
    Returns stats dict."""
    work = json.loads(Path(work_path).read_text(encoding="utf-8"))
    matched = 0
    unmatched = 0
    for row in work.get("rows", []):
        for img in row.get("images", []):
            if (img.get("decision") or "").lower() != "regen":
                continue
            orig = img.get("orig", "")
            if orig in url_mapping:
                img["new_url"] = url_mapping[orig]
                matched += 1
            else:
                unmatched += 1
    # Write back
    Path(work_path).write_text(json.dumps(work, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"matched": matched, "unmatched": unmatched, "total_mapping": len(url_mapping)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Pull regen URLs from Feishu Bitable into work.json")
    ap.add_argument("work_json", help="Path to work.json from the pipeline")
    ap.add_argument("--base-token", required=True, help="Feishu Base token")
    ap.add_argument("--table-id", required=True, help="Feishu Base table ID")
    ap.add_argument("--source-field", default="附件链接",
                    help="Field containing original URLs (default: 附件链接)")
    ap.add_argument("--new-field", default="图片转链接",
                    help="Field containing new URLs (default: 图片转链接)")
    ap.add_argument("--as", dest="as_identity", default="user", choices=["user", "bot"])
    args = ap.parse_args(argv)

    print(f"Fetching records from Feishu Base...", flush=True)
    mapping = fetch_records(
        args.base_token, args.table_id,
        args.source_field, args.new_field, args.as_identity,
    )
    print(f"  Got {len(mapping)} URL mappings.", flush=True)
    if not mapping:
        print("  No mappings found. Check field names or table contents.", flush=True)
        return 1

    print(f"Updating {args.work_json}...", flush=True)
    stats = update_work_json(args.work_json, mapping)
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    print(f"\nNext: run `tkvn.py finalize <xlsx> {args.work_json} <out.xlsx>` to write the sheet.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
