"""Sanity check: ensure core modules import and key callables exist."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REQUIRED = {
    "sheet_io": ["normalize_url", "extract_img_urls", "build_description_all",
                 "extract_text_content", "col_idx", "resolve_columns"],
    "batch_process": ["auto_process", "vision_audit", "translate_batch",
                      "_is_promo_url", "_is_already_cleaned_url", "KeyRoundRobin"],
    "run_pipeline": ["prepare", "finalize"],
    "check_sheet": ["CHECKS"],
}

problems = []
for mod, names in REQUIRED.items():
    try:
        m = importlib.import_module(mod)
    except Exception as e:
        problems.append(f"import {mod} failed: {e}")
        continue
    for n in names:
        if not hasattr(m, n):
            problems.append(f"{mod}.{n} missing")

if problems:
    print("FAIL")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("OK: all core modules import, all required callables present")
