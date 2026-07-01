# tk-vn-product-sheet-skill

**Process TikTok Shop Vietnam product spreadsheets from Chinese marketplaces.**

Translate titles/variants to Vietnamese, clean product images (remove brand
logos/watermarks, redraw text in Vietnamese), set brand/stock/SKU, extract
weight/dimensions from images — all in a URL→API→URL pipeline with no local
image downloads required.

## Architecture

```
xlsx → prepare → agent translates + vision pre-screens → batch image gen → finalize → xlsx
                                                                 ↓
                                                  Doubao Seedream 5.0 (2K)
                                                  or GPT-Image-2 (fallback)
```

## Quick start

```bash
git clone https://github.com/<your-org>/tk-vn-product-sheet-skill
cd tk-vn-product-sheet-skill
cp .env.example .env   # edit with your API keys
pip install openpyxl requests

# Process your sheet
python scripts/run_pipeline.py prepare "0630-tk.xlsx" work.json

# Vision pre-screen + batch image gen (see SKILL.md for details)

python scripts/run_pipeline.py finalize "0630-tk.xlsx" work.json "0630-tk.xlsx"
```

## Requirements

- Python 3.8+ with `openpyxl`, `requests`
- API keys (one of):
  - **Doubao Seedream 5.0** via Volcengine Ark (primary, 2K)
  - **GPT-Image-2** via hfsyapi (fallback, 1K)
  - **Agnes 2.0 flash** (vision pre-screening, optional)

## Key performance features

| Optimization | Factor | How |
|-------------|--------|-----|
| Vision pre-screen | 10-20x | Only 20-40% of images need generation. URL→classification, no download |
| URL→API→URL pipeline | 5x | No local file transfer, no image hosting needed |
| Image deduplication | 10x | 94 rows × 12 images → ~120 unique (product shots shared across variants) |
| Parallel API calls | 5-10x | Concurrent requests vs sequential |
| Direct image URL input | 3x | Both Doubao and hfsyapi accept URLs directly |

**94-row sheet, ~120 unique images: ~7-17 min total.**

## API key setup

```bash
# Primary (image generation)
ARK_API_KEY="your_volcengine_ark_key"

# Fallback (image generation)
HFSY_API_KEY="your_hfsyapi_gpt_image2_key"

# Optional (vision pre-screening)
AGNES_API_KEY="your_agnes_api_key"
```

## Full documentation

See [SKILL.md](SKILL.md) for the complete workflow, curl examples, field map,
troubleshooting, and Python batch recipes.

## Scripts

| Script | What it does |
|--------|-------------|
| `scripts/run_pipeline.py` | prepare (xlsx→JSON) + finalize (JSON→xlsx) |
| `scripts/sheet_io.py` | xlsx dump/apply utilities |
| `scripts/agnes_gen.py` | hfsyapi GPT-Image-2 wrapper |
| `scripts/agnes_read.py` | Vision reading via Agnes 2.0 flash |
| `scripts/check_sheet.py` | Validate processed xlsx |
| `scripts/check_pipeline.py` | Module availability check |

## License

MIT

