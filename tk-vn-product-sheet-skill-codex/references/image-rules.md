# Image Classification & Cleaning Rules

## ⚠️ Critical: Vision audit FIRST (don't skip)

**Every image must be audited by a vision LLM before deciding what to do.**
The prompt "去品牌/logo/水印" alone is not enough — you must first KNOW what's
in the image. Missing a brand/logo/watermark = IP infringement risk.

### Vision audit prompt (use Agnes 2.0 flash)

```bash
curl -X POST "https://apihub.agnes-ai.com/v1/chat/completions" \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-2.0-flash",
    "messages": [
      {"role": "system", "content": "Audit product image. Output JSON: {\"has_brand_name\":bool,\"brand_names_found\":[],\"has_logo\":bool,\"has_watermark\":bool,\"has_chinese_text\":bool,\"chinese_text_found\":[],\"is_promo_banner\":bool,\"needs_cleaning\":bool,\"cleaning_reason\":\"brand|logo|watermark|text|promo|none\",\"description\":\"\"}"},
      {"role": "user", "content": [
        {"type": "text", "text": "Audit this image for brand names, logos, watermarks, or Chinese text. Be thorough — do not miss small watermarks or corner logos."},
        {"type": "image_url", "image_url": {"url": "<IMAGE_URL>"}}
      ]}
    ],
    "max_tokens": 600
  }'
```

The audit returns structured JSON telling you exactly:
- `has_brand_name` + `brand_names_found` (e.g. ["izzue", "NIU"])
- `has_logo` / `has_watermark`
- `has_chinese_text` + `chinese_text_found`
- `is_promo_banner` (after-sales/store disclaimer/coupon)
- `needs_cleaning` + `cleaning_reason`

### Why audit matters (lessons learned)

| Missed item | Consequence |
|------------|-------------|
| Brand name in corner (izzue, NIU) | IP infringement, listing rejected |
| Store disclaimer image | Unprofessional, also contains brand |
| Watermark in background | IP issue |
| Chinese text in product photo | Vietnam shoppers can't read |

**Always audit. Never assume an image is "clean" without checking.**

## How to inspect an image

```
python scripts/fetch_image.py "<url>" /tmp/img_<n>.jpg
```
then Read the downloaded file. If the download fails (`__FAIL__`), you can still
send the URL to the vision API — it fetches the image server-side.

## Decision tree (based on vision audit)

⚠️ **删除规则只对产品描述(C列)图片生效。** 主图(R)/附图(S-Z)/变种图(AC)
**绝不删除**——它们只做清洗或保留。

### For 产品描述 (C column) images:

1. **`is_promo_banner: true` (客服图/营销图/优惠信息/售后信息)** → `decision: "delete"`
   - 与产品无关的图：客服卡片、店铺声明("认准XX专卖店")、优惠券、满减、
     售后/退换货、运费说明、活动 banner。从描述HTML里删掉,不重生成。
2. **has brand/logo/watermark/Chinese text** → `decision: "regen"` (clean it)
3. **clean product/spec image** → `decision: "keep"`

### For 主图/附图/变种图 (R / S-Z / AC):

1. **NEVER delete** — 即使看起来像促销图,也不删(它们是刊登必需的图位)。
2. **has brand/logo/watermark/Chinese text** → `decision: "regen"` (clean it)
   - Examples: "NIU" motorcycle logo, "舒适出行/记忆海绵增高垫" Chinese text.
   - If it has text: extract weight/dimensions into (`weight_kg`,`l`,`w`,`h`)
     per field-mapping.md while cleaning.
3. **clean product photo, no brand/text** → `decision: "keep"`.

> 换句话说: `delete` 决策**只能**用在 C列(产品描述)的图上。主图/附图/变种图
> 只有 `regen`(清洗) 或 `keep`(保留) 两种结果。

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
