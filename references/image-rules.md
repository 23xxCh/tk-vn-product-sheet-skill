# Image Classification & Agnes API Rules

## How to inspect an image

```
python scripts/fetch_image.py "<url>" /tmp/img_<n>.jpg
```
then Read the downloaded file. If the download fails (`__FAIL__`), you can still
send the URL to the Agnes API — it fetches the image server-side.

## Decision tree (set `decision` in work.json per image)

1. **Is this image the product itself?**
   - NO — it's a promo banner, after-sales/customer-service card, shipping
     template, store-coupon graphic, or event poster → `decision: "delete"`.
     These are removed from the description; never regenerated.
   - YES → continue.

2. **Does it contain a brand name, logo, or watermark?**
   - YES → `decision: "regen"`, run
     `python scripts/agnes_gen.py clean --image "<url>"` (no `--vi-text`).
     Put the returned URL in `new_url`.

3. **Does it contain readable text** (specs, material, weight, dimensions,
   usage instructions, size chart)?
   - YES → read the text, translate to Vietnamese, run
     `python scripts/agnes_gen.py clean --image "<url>" --vi-text "<vi>"`.
     Put the URL in `new_url`, the Vietnamese text in `vi_text`,
     `decision: "regen"`. Also extract weight/dimensions into the image entry
     (`weight_kg`, `l`, `w`, `h`) per field-mapping.md.
   - If it has BOTH a brand AND text: one regen call with `--vi-text` — the base
     prompt already removes brands.

4. **Clean product photo, no text/brand** → `decision: "keep"`.

## Promo / after-sales image tells (Chinese VN e-comm)

Delete any image whose content is primarily one of these (not the product):
- 大促 / 限时秒杀 / 满减 / 优惠券 / gift banners
- 售后 / 退换货 / 客服 / 7天无理由 / 运费 template cards
- 店铺关注 / 关注领券 / 收藏有礼
- 物流时效 / 发货说明
- 节日活动 (双11, 618, 年货节) posters
- Pure text "spec table" with no product — actually keep & translate these
  (they carry weight/dimension info); only delete if it's marketing copy.

When unsure whether a text card is marketing vs spec: marketing = delete,
spec/dimension = regen with translation.

## Agnes API details

- Endpoint: `POST https://apihub.agnes-ai.com/v1/images/generations`
- Auth: `Authorization: Bearer <AGNES_API_KEY>`
- Body:
  ```json
  {
    "model": "agnes-image-2.1-flash",
    "prompt": "<english instruction>",
    "size": "1024x1024",
    "extra_body": {"image": ["<input-url>"], "response_format": "url"}
  }
  ```
- Response: hosted URL at `data[0].url` (or top-level `url`/`image_url`).
- The script (`agnes_gen.py clean`) builds the prompt for you; just pass
  `--image` and optional `--vi-text`. The last stdout line is the new URL.

## Fidelity caveat (important)

Agnes has **no real mask/inpaint endpoint**. All edits are prompt-driven
diffusion — the model reimagines the image following your instruction while
trying to preserve the product. Consequences:
- Logo/watermark removal may leave artifacts or subtly alter the product.
- Vietnamese text redraw may be misspelled or poorly placed.
- For listings where pixel-perfect fidelity matters, this is best-effort.
- On any `__FAIL__` or visibly bad result, fall back to `decision: "keep"`
  (preserve the original URL) and list it in the final report.

## Cost / volume

94 rows × ~12 images = ~1100 images worst case. Batch rows 5–10 at a time.
Only regen images that actually need it (brand/text); clean product photos are
left alone — this keeps API calls far below the worst case.
