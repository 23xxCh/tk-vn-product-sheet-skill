---
name: tk-vn-product-sheet-skill
description: Process Chinese-source TikTok Shop product spreadsheets for Vietnam or any configured target language. Use for TikTok product-sheet preprocessing, row-level image URL deduplication, description-noise removal, multilingual title/variant/description localization, brand/logo/watermark cleaning with built-in image generation, public-image-URL writeback, 35-column alignment, and required-field validation.
---

# TikTok multilingual product sheet

Produce a platform-ready spreadsheet in a configured target language. Default to
Vietnamese (`vi`) only when the user does not specify a language.

## Required inputs

- Raw `.xlsx`
- Target language name and code, for example `Vietnamese/vi`, `Thai/th`, `English/en`
- Public image-hosting capability when cleaned images must be written as URLs

Never invent a public URL. Built-in image generation may create a temporary local
file; upload it through an available user-authorized hosting connector, then write
the returned HTTPS URL. If no uploader or hosted URL is available, stop before
image writeback and request one.

## Workflow

### 0. Preprocess the raw workbook

Run preprocessing before translation or image auditing:

```bash
python tkvn.py preprocess "raw.xlsx" -o "preprocessed.xlsx" \
  --dirty-manifest dirty-review.json
```

1. Within each row, inspect `主图(url)地址` and `附图一` through `附图八`.
   Preserve the first occurrence of each URL, remove later duplicates, and compact
   remaining URLs leftward without changing their order.
2. Semantically audit `Tiktok产品描述`, including text and every image.
   Remove content unrelated to the product: shop/customer-service cards,
   coupons/promotions, shipping/after-sales/return instructions, contact details,
   external links, generic payment/shipping/about-us templates, and unrelated
   images or prose.
3. Preserve product photos, specifications, dimensions, materials, usage
   instructions, and other product-specific content.
4. Record semantic removals in `dirty-review.json`; see
   [references/preprocessing.md](references/preprocessing.md).

The script handles deterministic URL deduplication and obvious text noise.
The agent remains responsible for semantic review of ambiguous text and images.

### 1. Prepare and localize

Use the target language explicitly:

```bash
python tkvn.py process "preprocessed.xlsx" \
  --target-language "Thai" --language-code "th"
```

For built-in-model mode, run `prepare`, fill `work.json` with localized titles,
variants and description text, and then continue with image audit.

Localization rules:

- Use natural marketplace language, not literal translation.
- Title starts with the product category and stays within 80 characters.
- Remove `原装/原厂/正品/专柜/官方` and counterfeit/absolute claims.
- Treat brands only as compatibility targets using natural target-language wording.
- Preserve numbers, units, model specifications and HTML structure.
- Localize variant names and values consistently.

Read `references/vietnamese-style.md` only when the target is Vietnamese.
For other languages, derive equivalent local marketplace wording and compliance
rules for that locale.

### 2. Audit every unique image

Audit all unique images before editing:

- Detect brand names, logos, watermarks, source-language text and promo banners.
- Main/sub/variant images: only `keep` or `regen`; never delete.
- Description images: delete unrelated promo/service content; regenerate
  product/spec images containing brand, watermark or source-language text.
- Extract visible weight and dimensions when available.

### 3. Edit images with built-in image generation

Use the user-supplied image prompt when present. Otherwise:

- Remove all brand/logo/shop/watermark elements.
- Translate source-language image copy to the configured target language.
- Preserve the product, specifications, quantities, colors, materials, layout,
  aspect ratio and lighting.
- Do not add replacement brands, promotional claims or invented information.

Inspect each generated result. Reject outputs with altered products, broken text,
wrong diacritics, missing specifications or obvious generation artifacts.
Use exact translated strings in the prompt for dense or important copy. Built-in
generation is not pixel-preserving by default: compare source/result and reject
unexpected cropping, square conversion, object changes or specification drift.

### 4. Obtain public URLs and write back

Follow [references/image-url-contract.md](references/image-url-contract.md):

1. Receive the generated image from the built-in model.
2. Upload it with an available user-authorized public image-hosting tool.
3. Require a stable `https://` URL; reject local paths, filenames, `file://`,
   `data:` URIs and expiring preview-only links.
4. Write the returned URL into `new_url` and then finalize the workbook.
5. Keep the original source URL in the work manifest for reprocessing/audit.

### 5. Deterministic output rules

- Brand column → empty
- Stock → `30`
- SKU → `YYYYMMDD` + five-digit sequence
- Video link → empty
- Output → exactly 35 columns
- Images → valid HTTPS URLs
- Required weight/dimensions → extract, infer from variants, or use a reasonable
  product-type estimate; never leave required values empty

### 6. Validate

Verify:

- Every title is localized and at most 80 characters.
- Description contains no unrelated text/images.
- No duplicate main/sub-image URL remains within a row.
- All regenerated image cells contain public HTTPS URLs.
- Brand is empty, stock is 30, video is empty, SKU format is valid.
- Output has exactly 35 columns and every required field is populated.

Treat validation as a delivery gate, not a report. Read and follow
[references/quality-gates.md](references/quality-gates.md). Validate the final
exported workbook because intermediate JSON can be correct while column alignment
or physical attributes are still wrong.

Use:

```bash
python tkvn.py check "output.xlsx" brand_set
python tkvn.py check "output.xlsx" stock_set
python tkvn.py check "output.xlsx" video_cleared
python tkvn.py check "output.xlsx" sku_format
python tkvn.py check "output.xlsx" image_urls_https
python tkvn.py check "output.xlsx" duplicate_images
python tkvn.py check "output.xlsx" required_fields
python tkvn.py check "output.xlsx" final_integrity
```

Do not deliver unless `final_integrity` passes.
