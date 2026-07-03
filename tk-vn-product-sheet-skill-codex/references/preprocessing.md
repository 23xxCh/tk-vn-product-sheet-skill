# Raw workbook preprocessing

## Semantic review manifest

Create a JSON file after reviewing every description text block and image:

```json
{
  "rows": {
    "2": {
      "remove_image_urls": [
        "https://example.com/customer-service-banner.jpg"
      ],
      "remove_text_exact": [
        "关注店铺领取优惠券"
      ]
    }
  }
}
```

Use exact row numbers from Excel. Put only confirmed unrelated content in the
manifest. Do not remove product specifications merely because they are presented
as a text card.

## Image deduplication

Deduplicate only within the nine listing-image cells of the same row:

`主图 → 附图一 → … → 附图八`

Comparison is case-insensitive after trimming whitespace. Preserve the first URL
and compact remaining unique URLs leftward. Do not deduplicate across different
rows; shared URLs between variants are valid.

## Dirty-description decisions

Remove:

- shop/customer-service/contact cards
- coupon, discount, campaign and follow-shop banners
- shipping, payment, returns, warranty and after-sales templates
- external social/contact information
- images or paragraphs for a different product

Keep:

- product photos and usage scenes
- size/specification tables
- material, feature and installation information
- compatibility information expressed compliantly

When uncertain, keep the item and flag it for review.
