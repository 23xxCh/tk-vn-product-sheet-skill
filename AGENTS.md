# AGENTS.md — tk-vn-product-sheet-skill (v4)

## Purpose

Process TikTok Shop Vietnam product spreadsheets:
1. Deterministic transforms (brand→Generic N/A, stock→30, SKU→date+seq, clear video)
2. Translate Chinese titles/variants → Vietnamese (≤80 chars, de-branded, IP-safe)
3. Vision pre-screen images → only clean images that need it via Doubao/GPT-Image-2
4. Extract weight/dimensions from image text via vision LLM

## Activation

`/tk-vn-product-sheet-skill 处理 <xlsx_path>`

## Quick workflow

1. `python scripts/run_pipeline.py prepare <xlsx> work.json`
2. Agent fills `work.json` translations: title (B), variant names/values (G-L)
3. **Vision pre-screen** each unique image URL via `agnes-2.0-flash`:
   - `clean` → keep (60-80% of images)
   - `brand`/`text` → send to Doubao/hfsyapi for cleaning
   - `promo` → delete
4. **Batch image gen** (only brand/text, 5-10 parallel):
   - Primary: Doubao Seedream 5.0 (2K)
   - Fallback: GPT-Image-2 via hfsyapi
5. Share main/sub URLs to all variant rows
6. `python scripts/run_pipeline.py finalize <xlsx> work.json <xlsx>`

## API keys (user-provided)

| Variable | Purpose |
|----------|---------|
| `ARK_API_KEY` | Doubao Seedream 5.0 (primary image gen, 2K) |
| `HFSY_API_KEY` | GPT-Image-2 (fallback image gen, 1K) |
| `AGNES_API_KEY` | Agnes 2.0 flash (vision pre-screening) |

See `SKILL.md` for full details, curl examples, and parallel batch recipes.
