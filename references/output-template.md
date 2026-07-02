# Output Template & Empty Value Check

## Output template: 35 columns

The input xlsx has 45 columns (A-AS). The TikTok Vietnam output template
(`template_tiktok.xlsx`) requires exactly **35 columns**.

### Rename
- Column O "价格(站点币种)" → "本地展示价(站点币种)"

### Drop extra columns (input cols 37-45)
- 备注, 店铺名, sku ID, 产品id, 全球产品id, 店铺币种, 创建时间, 更新时间, 平台刊登时间

### Final 35-column structure
```
1.分类id         2.产品标题       3.产品描述       4.品牌          5.产品属性     6.SKU
7.变种属性名称一  8.变种属性值一   9.变种属性名称二  10.变种属性值二  11.变种属性名称三 12.变种属性值三
13.识别码类型    14.识别码        15.本地展示价    16.库存         17.产品主图    18-25.附图一~八
26.视频链接      27.尺码图        28.变种主题1图片  29.重量(kg)    30.长(cm)      31.宽(cm)
32.高(cm)        33.仓库名称      34.货到付款      35.来源URL
```

Template headers (copy exactly, including `*` and `（必填）`):
```
*分类id\n（必填） | *产品标题\n（必填） | *产品描述\n（必填） | 品牌 | 产品属性 | SKU |
变种属性名称一 | 变种属性值一 | 变种属性名称二 | 变种属性值二 | 变种属性名称三 | 变种属性值三 |
识别码类型 | 识别码 | *本地展示价(站点币种)\n（必填） | *库存\n（必填） |
*产品主图(URL)地址\n（必填） | 附图一~附图八 | 视频链接 | 尺码图 | 变种主题1图片 |
*重量(kg)\n（必填） | *长(cm)\n（必填） | *宽(cm)\n（必填） | *高(cm)\n（必填） |
*仓库名称\n（必填） | 货到付款 | 来源URL
```

## Empty value check (REQUIRED before delivery)

After processing, verify all `*` required fields are filled. TikTok rejects
listings with empty required fields.

### Required columns (must be non-empty)
| Col | Field | Check |
|-----|-------|-------|
| 1 | 分类id | non-empty |
| 2 | 产品标题 | non-empty, ≤80 chars |
| 3 | 产品描述 | non-empty (HTML or text) |
| 15 | 本地展示价 | non-empty number |
| 16 | 库存 | = 30 |
| 17 | 产品主图 | non-empty URL |
| 29 | 重量(kg) | non-empty number |
| 30 | 长(cm) | non-empty number |
| 31 | 宽(cm) | non-empty number |
| 32 | 高(cm) | non-empty number |
| 33 | 仓库名称 | non-empty |

### Fill strategy for empty weight/dimensions

1. **Extract from image text** via vision LLM (best)
2. **Extract from variant values** (e.g. "3.0cm [dài 5m]" → W=3, L=500)
3. **Reasonable estimate** by product type (last resort):

| Product type | Weight (kg) | L×W×H (cm) |
|-------------|------------|-----------|
| Car armrest cushion | 0.3 | 40×25×15 |
| Window trim roll (1 roll) | 0.15 | 500×3×2 |
| Car sticker/decal | 0.05 | 10×1.5×0.1 |

> Never leave required fields empty. Use estimate if no data available.

### Verification script

```bash
python scripts/check_sheet.py "<xlsx>" brand_set
python scripts/check_sheet.py "<xlsx>" stock_set
python scripts/check_sheet.py "<xlsx>" video_cleared
python scripts/check_sheet.py "<xlsx>" sku_format
python scripts/check_sheet.py "<xlsx>" image_urls_https
```

All must report PASS.
