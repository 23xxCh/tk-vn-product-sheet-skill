# Feishu AI Field Shortcuts

飞书表格 AI 字段捷径配置指南。配合 `push-regen` / `pull-regen` 命令使用。

## 表格字段

| 字段名 | 类型 | 作用 |
|--------|------|------|
| 附件链接 | text | `push-regen` 写入原始图片 URL |
| 链接转附件 | attachment | AI：URL → 附件 |
| 生成图片 | attachment | AI：清洗+翻译越南语 |
| 图片转链接 | text | AI：附件 → URL（`pull-regen` 读取） |

## 文本翻译 Prompt

标题/描述/变种字段：

```
Translate the Chinese e-commerce product text into natural Vietnamese for TikTok
Shop Vietnam. Remove brand names, official/original/factory/direct-store claims,
contact information, and infringement-prone wording. Keep the meaning, product
type, specs, color, quantity, and applicable model information. Use concise,
local Vietnamese search terms. For titles, keep the result under 80 characters.
Return only the final Vietnamese text.
```

## 图片清洗 Prompt

```
Clean this product image for TikTok Shop Vietnam. Remove brand names, logos,
watermarks, Chinese/English promotional text, QR codes, contact information, and
store/customer-service banners. Translate all product text to Vietnamese.
Preserve the product, angle, color, material, and composition. Do not add new
claims or decorations.
```

## 与 CLI 配合使用

```bash
# 1. 推送需要处理的图片 URL
python tkvn.py push-regen work.json -t <token> -i <table>

# 2. 在表格 Web UI 配置 AI 字段捷径（字段→字段捷径→选择 AI 能力）
# 3. 等待 AI 处理完成（查看「图片转链接」字段是否有值）

# 4. 拉取结果
python tkvn.py pull-regen work.json -t <token> -i <table>
```
