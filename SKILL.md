---
name: tk-vn-product-sheet-skill
activation: /tk-vn-product-sheet-skill
description: >-
  Process TikTok cross-border e-commerce spreadsheets for Vietnam site:
  translate Chinese titles/variants to Vietnamese (de-branded, ≤80 chars),
  set brand→Generic N/A, stock→30, regenerate SKU, clear video links.
  Pre-screen product images via vision LLM → only send images containing
  brand/logo/watermark/text to Doubao Seedream 5.0 (2K) or GPT-Image-2
  for cleaning (remove brand/logo/watermark + translate text to Vietnamese).
  All URL→API→URL — no local file downloads needed. Triggers: tk越南站表格,
  tiktok产品表, 电商表格翻译越南语, 产品图去logo水印, 跨境电商数据清洗.
license: MIT
metadata:
  author: tk-vn-product-sheet-skill
  version: 4.0.0
  created: 2026-07-01
  last_reviewed: 2026-07-01
  review_interval_days: 90
  repository: https://github.com/<user>/tk-vn-product-sheet-skill
  os_family: cross-platform
  provenance:
    - source: https://github.com/mageia/skills-hub/skills/waninter-creative
      license: MIT
      adapted: true
    - source: agent-skill-creator (https://github.com/FrancyJGLisboa/agent-skill-creator)
      license: MIT
---

# /tk-vn-product-sheet-skill

Process Chinese-source TikTok Shop product spreadsheets into Vietnam-site-ready
listings. **Full URL→API→URL pipeline** — no local image downloads needed,
no image hosting required.

**For AI agents** — this skill tells you exactly how to process the spreadsheet
step by step, with curl commands ready to copy-paste.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/<user>/tk-vn-product-sheet-skill.git

# 2. Set API keys
export ARK_API_KEY="your_doubao_key_here"
export HFSY_API_KEY="your_hfsyapi_key_here"

# 3. Prepare (deterministic: brand/stock/SKU/video)
python scripts/run_pipeline.py prepare "0630-tk.xlsx" work.json

# 4. Translate titles/variants (agent fills work.json translations)

# 5. Vision pre-screen → image gen → write back (see workflow below)

# 6. Finalize
python scripts/run_pipeline.py finalize "0630-tk.xlsx" work.json "0630-tk.xlsx"
```

---

## Architecture

```
┌─ xlsx ───────────────────────────────────────────────────┐
│ 94 rows, 45 cols (A-AS): 标题/品牌/库存/SKU/主图/附图/变种图 │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 1: run_pipeline.py prepare ────────────────────────┐
│  Deterministic transforms:                                │
│  • 品牌D → Generic N/A                                    │
│  • 库存Q → 30                                             │
│  • 视频AA → cleared                                       │
│  • SKU F → YYYYMMDD + 5-digit seq                        │
│  • 图片URL → https:// normalize                           │
│  • Output: work.json (deduplicated image inventory)       │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 2: Agent translates (fills work.json) ─────────────┐
│  • 标题B → Vietnamese, ≤80 chars, de-brand                │
│  • 变种名GIK → Vietnamese (Phân loại màu, v.v.)          │
│  • 变种值HJL → de-brand + Vietnamese                      │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 3: Vision pre-screen (classify images by URL) ─┐
│  For each unique image URL, ask a vision LLM:          │
│  "この画像にブランド名/ロゴ/透かし/中国語テキストがありますか?"│
│  → clean: keep (no processing needed)                 │
│  → brand: needs brand/logo/watermark removal           │
│  → text: has Chinese text → translate to Vietnamese    │
│  → promo: after-sales/promo banner → delete            │
│                                                        │
│  Vision API: POST agnes-2.0-flash /v1/chat/completions │
│  Input: image URL (no local download)                  │
│  Output: classification JSON                           │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 4: Batch image generation ─────────────────────────┐
│  Only process images classified as brand/text.            │
│  Parallel batches (5-10 concurrent requests):             │
│                                                        │
│  Primary: Doubao Seedream 5.0 (2K)                      │
│  POST https://ark.cn-beijing.volces.com/api/v3/...       │
│  { "model":"doubao-seedream-5-0-260128",                 │
│    "prompt":"Remove brand names, logos and watermarks    │
│              from the image, and translate all text      │
│              to Vietnamese.",                            │
│    "image":"<ORIGINAL_URL>",                             │
│    "response_format":"url", "size":"2K" }               │
│  → returns hosted URL (24hr TOS signed)                  │
│                                                        │
│  Fallback: GPT-Image-2 (1K)                              │
│  POST https://www.hfsyapi.cn/v1/images/generations       │
│  → returns OSS hosted URL (24hr)                         │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 5: run_pipeline.py finalize ──────────────────────┐
│  Write all results back to xlsx:                        │
│  • Translations (title, variants)                       │
│  • Cleaned image URLs (main/sub → all variant rows)    │
│  • Variant image URLs (each row individually)           │
│  • Rewritten description HTML (cleaned URLs swapped)   │
│  • Extracted weight/dimensions (if vision found them)  │
│  • Backs up original → .xlsx.bak                        │
└──────────────────────────────────────────────────────────┘
```

---

## API Keys (required)

Create an `.env` file in the skill directory (or export as env vars):

```bash
# Primary: Doubao Seedream 5.0 (2K, best quality, 图生图)
ARK_API_KEY="your_ark_api_key"

# Fallback: GPT-Image-2 via hfsyapi (1K, when Doubao fails)
HFSY_API_KEY="your_hfsyapi_key"

# Vision pre-screening: Agnes 2.0 flash (classifies images by URL)
AGNES_API_KEY="your_agnes_api_key"
```

> **Open source note**: API keys are user-specific. The `.env` file is
> `.gitignore`d. Users must provide their own keys for the APIs they choose.

---

## Core Workflow

### Step 1 — Prepare (deterministic transforms)

```bash
python scripts/run_pipeline.py prepare "<xlsx_path>" work.json
```

Reads the xlsx, computes SKUs, normalizes URLs, deduplicates images,
outputs `work.json`. Does NOT modify the xlsx.

### Step 2 — Fill translations

Edit `work.json` manually or via script. For each row, set:

```json
{
  "row_index": 2,
  "translate": {
    "B": "Đệm nâng cao hộp tựa tay ô tô, bảo vệ tựa tay, da dày cao cấp, đa năng",
    "G": "Phân loại màu",
    "H": "Đệm nâng cao - đa năng + túi đựng"
  }
}
```

Rules:
- **Title (B)**: Chinese → Vietnamese, ≤80 chars, remove 原装/原厂
- **Brand words**: rewrite as `phù hợp với [thương hiệu] [mẫu mã]` (compatible with)
- **Variant names**: `颜色分类→Phân loại màu`, `商品规格→Quy cách sản phẩm`
- **Variant values**: de-brand + translate to Vietnamese

### Step 3 — Vision pre-screening (classify images WITHOUT downloading)

For each unique image URL in `work.json`, classify it by sending the URL
directly to a vision LLM. No local downloads needed.

**Using Agnes 2.0 flash (vision LLM):**

```bash
curl -X POST "https://apihub.agnes-ai.com/v1/chat/completions" \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-2.0-flash",
    "messages": [
      {"role": "system", "content": "Classify this product image. Output one word only: clean / brand / text / promo"},
      {"role": "user", "content": [
        {"type": "text", "text": "Does this image contain brand names, logos, watermarks, or Chinese text? Is it a product photo or a promo banner?"},
        {"type": "image_url", "image_url": {"url": "<IMAGE_URL>"}}
      ]}
    ],
    "max_tokens": 50
  }'
```

**Classification categories:**

| Category | Definition | Action |
|----------|-----------|--------|
| `clean` | Product photo, no brand/logo/watermark/text | `decision: "keep"` — skip API call |
| `brand` | Has brand name/logo/watermark (no text) | `decision: "regen"` → image gen API |
| `text` | Has Chinese/Vietnamese/English readable text | `decision: "regen"` + extract text → image gen API |
| `promo` | Promo banner, after-sales card, coupon, shipping info | `decision: "delete"` — remove from listing |

**Why this is fast:**
- ✅ Vision LLM reads the URL directly — no local download
- ✅ Only images classified as `brand` or `text` go through the image gen API
- ✅ Clean images (typically 60-80% of total) are skipped entirely
- ✅ Classification costs < $0.001 per image vs image gen at $0.02-0.05

### Step 4 — Batch image generation

Process only `brand`/`text` images. Send multiple requests in parallel.

**Primary — Doubao Seedream 5.0** (2K, best quality):

```bash
curl -X POST "https://ark.cn-beijing.volces.com/api/v3/images/generations" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seedream-5-0-260128",
    "prompt": "Remove brand names, logos and watermarks from the image, and translate all text to Vietnamese.",
    "image": "<IMAGE_URL>",
    "sequential_image_generation": "disabled",
    "response_format": "url",
    "size": "2K",
    "watermark": false
  }'
```

**Response:** `{"data": [{"url": "https://...tos-cn-beijing...jpeg"}]}`

**Fallback — GPT-Image-2 via hfsyapi** (when Doubao fails):

```bash
curl -X POST "https://www.hfsyapi.cn/v1/images/generations" \
  -H "Authorization: Bearer $HFSY_API_KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: curl/7.68.0" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "Remove brand names, logos and watermarks from the image, and translate all text to Vietnamese.",
    "reference_images": ["<IMAGE_URL>"],
    "size": "1024x1024",
    "n": 1,
    "response_format": "url"
  }'
```

**Speed tips:**
- **Deduplicate first**: 94 rows × 12 images = 1128 → typically only **120 unique images**
- **Parallelize**: Run 5-10 concurrent curl requests (most APIs support concurrent calls)
- **For gw.alicdn images**: Some CDNs block API fetch. Download to temp → base64 → send as data URI to hfsyapi:
  ```bash
  curl -s "<GW_ALICDN_URL>" | base64 -w0 > /tmp/img_b64.txt
  # Then use "data:image/jpeg;base64,$(cat /tmp/img_b64.txt)" in reference_images
  ```

### Step 5 — Extract weight/dimensions (from text-containing images)

When an image is classified as `text`, use the vision LLM to also extract
any weight or dimension information:

```bash
curl -X POST "https://apihub.agnes-ai.com/v1/chat/completions" \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-2.0-flash",
    "messages": [
      {"role": "system", "content": "Extract product weight and dimensions from the image. If weight is shown in g/lb/jin, convert to kg. If dimensions are shown, extract as LxWxH in cm. Output JSON."},
      {"role": "user", "content": [
        {"type": "text", "text": "Read all text in this product image. Extract weight (convert to kg) and dimensions (cm)."},
        {"type": "image_url", "image_url": {"url": "<IMAGE_URL>"}}
      ]}
    ],
    "max_tokens": 512
  }'
```

→ Write to `row.weight_kg`, `row.l`, `row.w`, `row.h` in work.json

### Step 6 — Apply shared URLs

Main image and sub image results are shared across all variant rows of the
same product. After processing the first row's images, copy the results
to all other rows of that product.

### Step 7 — Finalize

```bash
python scripts/run_pipeline.py finalize "<xlsx>" work.json "<xlsx>"
```

Writes everything back. Backs up original first.

---

## Field Map

| Col | Field | Description | Treatment |
|-----|-------|-------------|-----------|
| B | 产品标题 | Product title | Agent: Chinese→Vietnamese, ≤80, de-brand |
| C | Tiktok产品描述 | HTML `<img src=…>` description | Drop promo imgs, swap cleaned URLs |
| D | 品牌 | Brand name | Deterministic: `Generic N/A` |
| F | sku | SKU number | Deterministic: `YYYYMMDD + 5-digit` |
| G | 变种属性名称一 | Variant attr name 1 | Agent: Vietnamese |
| H | 变种属性值一 | Variant attr value 1 | Agent: de-brand + Vietnamese |
| I/J | 变种属性名称/值二 | Variant attr 2 | Same as G/H |
| K/L | 变种属性名称/值三 | Variant attr 3 | Same as G/H |
| Q | 库存 | Stock quantity | Deterministic: `30` |
| R | 主图(url)地址 | Main product image | Vision pre-screen → Doubao gen → share to all rows |
| S-Z | 附图一~八 | Sub images 1-8 | Same as R. Sub6 = shop disclaimer → delete |
| AA | 视频连接 | Video link | Deterministic: clear |
| AC | 变种主题1图片 | Variant theme image | Vision pre-screen → Doubao gen (each row different) |
| AD | 重量(kg) | Weight in kg | Vision extract from image text |
| AE/AF/AG | 长/宽/高 | Dimensions L/W/H in cm | Vision extract from image text |

---

## Recipes

### Batch processing script

```python
import requests, json, concurrent.futures

def classify_image(url):
    """Vision pre-screen: returns 'clean'|'brand'|'text'|'promo'"""
    resp = requests.post("https://apihub.agnes-ai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {AGNES_KEY}"},
        json={"model":"agnes-2.0-flash","messages":[
            {"role":"system","content":"Classify: clean/brand/text/promo"},
            {"role":"user","content":[{"type":"text","text":"Classify this product image"},{"type":"image_url","image_url":{"url":url}}]}
        ]})
    return resp.json()["choices"][0]["message"]["content"].strip().lower()

def gen_image(url):
    """Doubao seedream: returns cleaned image URL"""
    resp = requests.post("https://ark.cn-beijing.volces.com/api/v3/images/generations",
        headers={"Authorization": f"Bearer {ARK_KEY}"},
        json={"model":"doubao-seedream-5-0-260128",
              "prompt":"Remove brand names, logos and watermarks from the image, and translate all text to Vietnamese.",
              "image": url, "response_format":"url", "size":"2K"})
    return resp.json()["data"][0]["url"]

# Deduplicate + classify
unique_urls = {img["orig"] for row in work["rows"] for img in row["images"]}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    classifications = dict(zip(unique_urls, ex.map(classify_image, unique_urls)))

# Only generate for brand/text
to_gen = [url for url,cls in classifications.items() if cls in ("brand","text")]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    new_urls = dict(zip(to_gen, ex.map(gen_image, to_gen)))
```

---

## Batch auto-process (one command, fastest)

```bash
# Set keys
export ARK_API_KEY="..."
export HFSY_API_KEY="..."
export AGNES_API_KEY="..."

# One command: prepare → vision screen → parallel gen → finalize
python scripts/batch_process.py "0630-tk.xlsx"
```

This script does everything in one shot:
1. `prepare` — deterministic transforms (<1s)
2. Vision pre-screen all unique images (10× parallel, ~2min for 120 images)
3. Batch image gen for brand/text only (5× parallel Doubao→hfsyapi fallback)
4. Share URLs + finalize

**No bash timeouts, no manual restart, no sequential waiting.**

---

## Why This Is Fast

| Optimization | Speedup | How |
|-------------|--------|-----|
| **Vision pre-screen** | 10-20× | Classify by URL (no download). Only 20-40% of images need generation. Rest are kept as-is. |
| **Deduplication** | 10× | 94 rows → ~120 unique images (not 1128). Product shots shared across variant rows. |
| **Parallel API calls** | 5-10× | 10 concurrent vision + 5 concurrent gen requests instead of sequential. |
| **Direct URL input** | 3× | Doubao/hfsyapi accept image URLs directly (no base64 encoding needed in most cases). |
| **Single script** | 2× | No bash timeout, no manual restart, no context loss between steps. |

**Estimated time for 94-row sheet (120 unique images):**
- Vision pre-screen (120 × 1s, 10 concurrent): ~**12 seconds**
- Image generation (30-40 images × 30s, 5 concurrent): ~**3-5 minutes**
- Deterministic + finalize: ~**1 second**
- **Total: ~3-5 minutes** (vs 60+ min with sequential one-at-a-time)

## Benchmark (actual run on 94-row sheet)

| Method | Time | API calls |
|--------|------|-----------|
| Sequential, no pre-screen ❌ | ~60 min | 120× gen |
| Sequential, with pre-screen | ~15-20 min | 120× vision + ~35× gen |
| **Parallel + pre-screen (batch_process.py) ✅** | **~3-5 min** | **120× vision(10par) + ~35× gen(5par)** |

---

## URL Expiry

Both Doubao (TOS) and hfsyapi (OSS) return **signed URLs** with ~24hr validity.
This is sufficient for:
1. Paste URLs into spreadsheet
2. Upload to TikTok Shop platform (TikTok caches to its own CDN)
3. Once cached, expiry doesn't matter

If re-upload is needed later, run the pipeline again from Step 3 (the original
image URLs remain unchanged).

---

## Installation (for open source users)

```bash
git clone https://github.com/<user>/tk-vn-product-sheet-skill.git
cd tk-vn-product-sheet-skill
pip install openpyxl requests

# Set up API keys
cp .env.example .env
# Edit .env with your API keys
```

Requirements:
- Python 3.8+
- `openpyxl` (xlsx reading/writing)
- `requests` (API calls)
- API keys for Doubao Seedream / hfsyapi / Agnes vision

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_pipeline.py` | `prepare` (xlsx→work.json) + `finalize` (work.json→xlsx) |
| `scripts/sheet_io.py` | xlsx dump/apply utilities |
| `scripts/agnest_gen.py` | hfsyapi GPT-Image-2 wrapper |
| `scripts/agnes_read.py` | Vision reading via Agnes 2.0 flash |
| `scripts/fetch_image.py` | Download image URL to file (fallback only) |
| `scripts/check_sheet.py` | Validate processed xlsx |
| `scripts/check_pipeline.py` | Module availability check |

---

## References

- `references/field-mapping.md` — Full column map and per-field rules
- `references/image-rules.md` — Image classification rules + API details
- `references/vietnamese-style.md` — Vietnamese title/variant style + IP-safe rules

---

## License

MIT — use freely, modify, share.
