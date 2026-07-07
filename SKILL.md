---
name: tk-vn-product-sheet-skill
description: Process TikTok China product sheets for TikTok Vietnam. Use when processing xlsx files from taobao/1688 for TikTok Shop Vietnam listing. Triggers: "处理表格", "越南站", "TikTok越南", "清洗商品数据", "翻译越南语"
---

# TK VN Product Sheet Skill

## Workflow

### Step 1: Local Audit (确定性)
- Run vision audit on all unique images using 4-layer fallback chain
- **Completion**: work.json created with audit results for all images
- **Freedom**: Low — exact prompt, exact fallback order

### Step 2: Translation (确定性)
- Translate titles, variants, descriptions using 2-layer fallback
- **Completion**: all translatable fields filled in work.json, ≤80 chars for titles
- **Freedom**: Medium — follow vietnamese-style.md rules, but prompt wording flexible

### Step 3: Deterministic Cleaning (确定性)
- Brand → empty, Stock → 30, SKU → YYYYMMDD00001, Video → delete
- Image URLs → https, Price column → rename to 本地展示价 (drop empty column)
- **Completion**: work.json updated with all deterministic values
- **Freedom**: Low — exact values, exact order

### Step 4: Image Generation (灵活性)
- **Option A**: Local generation (全自动, use --hfsy-key)
- **Option B**: Feishu AI (推荐, use push-regen + pull-regen)
- **Completion**: work.json updated with generated URLs or keep decisions
- **Freedom**: High — user chooses local vs Feishu

### Step 5: Write Back (确定性)
- Run finalize to write work.json back to xlsx
- **Completion**: output.xlsx created with all changes applied, no column misalignment
- **Freedom**: Low — exact command, exact order

## Error Handling

| Error | Action |
|-------|--------|
| API rate limit (429) | Retry with exponential backoff (max 3 attempts) |
| Network timeout | Retry with backoff |
| Vision audit fails all models | Mark as needs_cleaning (conservative) |
| Translation fails | Keep original text, flag in report |
| Excel locked | Retry save 10 times, then save with _final suffix |
| Feishu polling timeout | Manual finalize after user confirms completion |
| Image download fails | Retry with different User-Agent/Referer, then skip |

## Gotchas

- **列错位**: Deleting empty columns shifts column positions. Always delete BEFORE writing data, then re-resolve columns.
- **base64 cache**: Signed URLs (Expires=) should not be cached — they expire and mask refreshed URLs.
- **Translation race**: Multiple threads translating same text can produce different results. Use field-level cache + lock.
- **work.json overwrite**: Re-running process overwrites work.json. Use --checkpoint to resume, or delete work.json first.
- **Image URL expiration**: OSS signed URLs expire in ~24 hours. Process immediately.
- **gw.alicdn.com firewall**: Use multiple User-Agent/Referer + retry for downloads.
- **Delete rule**: Only delete C column (description) images. Never delete R/S-Z/AC images.
- **Field name hardcoded**: _count_ready checks for "图片转链接". Use --new-field to customize.
- **Weight/dimension extraction**: Disabled due to unreliable data from vision models.
- **Chinese character residue**: Translation prompt may leave Chinese chars. Post-process to strip.
- **Promo image detection**: URL patterns (paybtn, kefu, coupon) mark as delete. Vision audit may miss some.
- **Multi-key rotation**: Comma-separated keys rotate per request. If one key fails, next request uses next key.

## References

- Translation rules: [references/vietnamese-style.md](references/vietnamese-style.md)
- Image audit rules: [references/image-rules.md](references/image-rules.md)
- Field mapping: [references/field-mapping.md](references/field-mapping.md)
- Feishu AI shortcuts: [references/feishu-ai-field-shortcuts.md](references/feishu-ai-field-shortcuts.md)

## CLI Commands

```bash
# Full pipeline (local generation)
python tkvn.py process "input.xlsx" --kimi-key KEY --hfsy-key "K1,K2" --gen-size 4K

# Local audit + translation only
python tkvn.py process "input.xlsx" --kimi-key KEY --no-gen

# Feishu workflow (recommended)
python tkvn.py push-regen work.json -t TOKEN -i TABLE
python tkvn.py pull-regen work.json -t TOKEN -i TABLE
python tkvn.py finalize "input.xlsx" work.json "output.xlsx"

# Verification
python tkvn.py check "output.xlsx" brand_set
python tkvn.py check "output.xlsx" sku_format
python tkvn.py eval

# Utilities
python tkvn.py rollback "output.xlsx"  # Restore from .bak
python tkvn.py watch  # Folder watcher mode
```

## Environment Variables

```bash
KIMI_API_KEY=xxx      # Vision audit + translation (primary)
BAILIAN_API_KEY=xxx   # Vision audit (backup, supports URL direct)
ARK_API_KEY=xxx       # Translation (backup)
HFSY_API_KEY=xxx      # Image generation (comma-separated for rotation)
AGNES_API_KEY=xxx     # Vision audit (last resort)
```

## Determinism Guarantees

- **Audit cache**: `_audit_cache.json` — same URL always returns same audit result
- **Translation cache**: `_trans_cache` — same text always returns same translation (field-level)
- **base64 cache**: `_img_cache/` — downloaded images cached locally (signed URLs excluded)
- **work.json resume**: Re-running process resumes from work.json (uses cached results)
- **Already-processed skip**: hfsyapi/coze/~crop URLs marked as keep without re-audit
- **URL pattern detection**: Promo/service URLs matched by regex, marked as delete
- **Exception classification**: 401/403/404 → no retry; 429/5xx → retry; timeout → retry
