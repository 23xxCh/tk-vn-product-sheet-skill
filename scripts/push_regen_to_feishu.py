"""Push image URLs that need regeneration to a Feishu Bitable.

Reads work.json from the pipeline, extracts all images marked as "regen",
deduplicates by URL, and pushes them to a Feishu Base table's "附件链接"
field in batches of 200.

Usage:
  python scripts/push_regen_to_feishu.py <work.json> --base-token X --table-id Y
  python scripts/push_regen_to_feishu.py <work.json> --base-token X --table-id Y --field "附件链接"
  python scripts/push_regen_to_feishu.py <work.json> --base-token X --table-id Y --include-skus

The table should have a text field (default: 附件链接) to receive the URLs.
After pushing, configure Feishu AI field shortcuts to:
  1. 链接转附件 (URL -> attachment)
  2. 生成图片 (AI image cleaning)
  3. 图片转链接 (attachment -> URL)
Then export the results and feed them back via finalize.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


BATCH_SIZE = 200  # Feishu batch create limit


def collect_regen_urls(work_path: str, include_skus: bool = False) -> list[dict]:
    """Read work.json, return list of {url, sku?, col?} for images marked regen.
    Filters out non-URL values (e.g. numeric 0.3, 0.0, 'nan')."""
    work = json.loads(Path(work_path).read_text(encoding="utf-8"))
    seen: set[str] = set()
    records: list[dict] = []
    for row in work.get("rows", []):
        sku = row.get("sku", "")
        for img in row.get("images", []):
            if (img.get("decision") or "").lower() != "regen":
                continue
            url = img.get("new_url") or img.get("orig") or ""
            # Filter out non-URL values (numeric, 'nan', '0', etc.)
            if not url or not isinstance(url, str):
                continue
            url = url.strip()
            if not url or not url.startswith(("http://", "https://", "//")):
                continue
            if url in seen:
                continue
            seen.add(url)
            rec = {"url": url}
            if include_skus:
                rec["sku"] = sku
                rec["col"] = img.get("col", "")
            records.append(rec)
    return records


def batch_create(base_token: str, table_id: str, fields: list[str],
                 rows: list[list], as_identity: str = "user") -> dict:
    """Call lark-cli base +record-batch-create."""
    payload = {"fields": fields, "rows": rows}
    lark_cli = shutil.which("lark-cli") or "lark-cli"
    # Write payload to a relative temp file (lark-cli requires relative paths)
    payload_path = f"_push_payload_{os.getpid()}.json"
    Path(payload_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    cmd = [
        lark_cli, "base", "+record-batch-create",
        "--base-token", base_token,
        "--table-id", table_id,
        "--as", as_identity,
        "--json", f"@{payload_path}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        Path(payload_path).unlink(missing_ok=True)
    if result.returncode != 0:
        try:
            err = json.loads(result.stderr or result.stdout)
        except json.JSONDecodeError:
            err = {"raw": (result.stderr or result.stdout)[:500]}
        return {"ok": False, "error": err}
    try:
        return {"ok": True, "data": json.loads(result.stdout)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": result.stdout[:500]}


def push_to_feishu(work_path: str, base_token: str, table_id: str,
                   field_name: str = "附件链接", include_skus: bool = False,
                   as_identity: str = "user") -> dict:
    records = collect_regen_urls(work_path, include_skus)
    if not records:
        print("No regen URLs found in work.json.")
        return {"pushed": 0, "records": []}

    print(f"Found {len(records)} unique regen URLs to push.")

    # Build field list
    fields = [field_name]
    if include_skus:
        fields += ["SKU", "列"]  # Extra fields for tracking

    total_pushed = 0
    all_record_ids: list[str] = []
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        rows = []
        for rec in batch:
            row = [rec["url"]]
            if include_skus:
                row += [rec.get("sku", ""), rec.get("col", "")]
            rows.append(row)
        print(f"  Pushing batch {i // BATCH_SIZE + 1} ({len(batch)} rows)...", flush=True)
        result = batch_create(base_token, table_id, fields, rows, as_identity)
        if not result.get("ok"):
            print(f"  ERROR: {result.get('error')}")
            break
        data = result.get("data", {}).get("data", {})
        rids = data.get("record_id_list", [])
        all_record_ids.extend(rids)
        total_pushed += len(batch)
        print(f"  OK ({len(rids)} records created)")

    print(f"\nPushed {total_pushed} URLs to Feishu Base.")
    return {"pushed": total_pushed, "record_ids": all_record_ids}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Push regen URLs to Feishu Bitable")
    ap.add_argument("work_json", help="Path to work.json from the pipeline")
    ap.add_argument("--base-token", required=True, help="Feishu Base token")
    ap.add_argument("--table-id", required=True, help="Feishu Base table ID")
    ap.add_argument("--field", default="附件链接",
                    help="Field name to receive URLs (default: 附件链接)")
    ap.add_argument("--include-skus", action="store_true",
                    help="Also write SKU and column for tracking (requires SKU/列 fields)")
    ap.add_argument("--as", dest="as_identity", default="user", choices=["user", "bot"])
    args = ap.parse_args(argv)

    report = push_to_feishu(
        args.work_json, args.base_token, args.table_id,
        args.field, args.include_skus, args.as_identity,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("pushed", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
