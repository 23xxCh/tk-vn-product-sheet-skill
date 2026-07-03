# Quality gates learned from production use

Run these gates in order. Do not deliver merely because the pipeline exited
successfully.

## 1. Preprocessing gate

- Count duplicate listing-image URLs before and after preprocessing.
- Confirm deduplication is row-local; do not remove URLs shared by variant rows.
- Review every removed description block. Product specifications and installation
  cards are not dirty data.

## 2. Localization gate

- Check every title is in the configured target language and ≤80 characters.
- Check variant names/values use consistent local terminology.
- Preserve numbers, units, dimensions and model identifiers.
- Remove brand-as-product wording while retaining compliant compatibility wording.

## 3. Image gate

For every regenerated image compare source and result:

- same product count, geometry, color, material, accessories and viewpoint
- same numeric specifications, units and functional icons
- no brand/logo/shop/watermark remains
- all source-language copy is replaced with correct target-language text
- no garbled characters, missing diacritics, invented claims or altered objects
- same aspect ratio; reject unexpected cropping or forced square output

Use exact target-language strings in the edit prompt when legibility matters.
Regenerate once with a single focused correction. If fidelity still fails, flag
the image; never silently substitute a materially altered product.

## 4. URL gate

- Upload only an accepted final image.
- Verify the URL starts with `https://` and resolves to the image itself.
- Never write a local path, filename, data URI, preview page or invented URL.
- Preserve source URL → generated URL mapping for audit and retry.

## 5. Workbook gate

Validate the exported workbook, not only `work.json`:

- exactly 35 columns
- headers match the TikTok template
- brand empty, stock 30, video empty, SKU valid
- no duplicate main/sub image URL within a row
- all required fields populated
- weight and dimensions are positive numbers
- regenerated and description-image references are public HTTPS URLs

Run:

```bash
python tkvn.py check "output.xlsx" final_integrity
```

Any failure blocks delivery.
