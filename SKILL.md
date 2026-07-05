# TK VN Product Sheet Skill

处理中国来源的 TikTok 商品表格，自动生成越南站可用的刊登表格。

CLI 统一入口：`python tkvn.py <command>`

## 两种工作流

### 飞书生图模式（推荐，稳定）

本地做确定性清洗+翻译+审计，生图委托飞书 AI 字段捷径：

```bash
# 1. 本地处理（审计+翻译，不生图）
python tkvn.py process "input.xlsx" --kimi-key $KIMI_API_KEY --no-gen

# 2. 推送需重新生成的图片URL到飞书
python tkvn.py push-regen work_auto.json \
  --base-token <token> --table-id <table>

# 3. 在飞书 Web UI 配置 AI 字段捷径处理图片后

# 4. 拉取飞书处理后的新URL
python tkvn.py pull-regen work_auto.json \
  --base-token <token> --table-id <table>

# 5. 写回 xlsx
python tkvn.py finalize "input.xlsx" work_auto.json "output.xlsx"
```

### 本地生图模式（全自动）

一条命令完成全部流程：

```bash
python tkvn.py process "input.xlsx" \
  --kimi-key $KIMI_API_KEY \
  --hfsy-key "key1,key2,key3" \
  --gen-size 4K --workers 50
```

## CLI 命令速查

```bash
# 全自动流水线（本地生图）
python tkvn.py process "input.xlsx"
  --kimi-key KEY          # Kimi 视觉审计 + 翻译（首选）
  --bailian-key KEY        # 阿里云百炼 Qwen-VL（备用）
  --hfsy-key "K1,K2"       # 生图 API keys，逗号分隔多key轮换
  --doubao-key KEY         # minimax-m3 + 豆包生图
  --agnes-key KEY          # agnes-2.0-flash 视觉审计备用
  --no-gen                 # 跳过本地生图，仅输出 work.json
  --workers N              # 生图并发数（0=自动）
  --checkpoint PATH        # 断点续传文件路径
  --gen-size 4K            # 生图分辨率 [1K|2K|4K]

# 分步模式
python tkvn.py prepare "input.xlsx"     # 仅确定性清洗
python tkvn.py finalize "input.xlsx" work.json "out.xlsx"  # 写回

# 飞书生图子命令
python tkvn.py push-regen work.json -t <token> -i <table>   # 推送URL到飞书
python tkvn.py pull-regen work.json -t <token> -i <table>   # 拉取新URL

# 校验
python tkvn.py check "output.xlsx" brand_set
python tkvn.py check "output.xlsx" sku_format

# 评测
python tkvn.py eval

# 文件夹监听
python tkvn.py watch
```

## 环境变量

```bash
KIMI_API_KEY=xxx      # Kimi/Moonshot（视觉审计+翻译首选）
BAILIAN_API_KEY=xxx    # 阿里云百炼 Qwen-VL（视觉审计备用，支持URL直传）
ARK_API_KEY=xxx        # Volcengine（minimax-m3翻译+豆包生图）
HFSY_API_KEY=xxx       # hfsyapi（nano-banana-2/GPT-Image-2生图），支持逗号分隔多key
AGNES_API_KEY=xxx      # agnes-2.0-flash（视觉审计最后备用）
```

## 视觉审计（4层回退链）

| 优先级 | 模型 | 端点 | 传图方式 |
|--------|------|------|---------|
| 1 | Kimi moonshot-v1-8k-vision | api.moonshot.cn | base64 |
| 2 | 阿里云百炼 qwen-vl-plus | dashscope.aliyuncs.com | URL→base64 |
| 3 | minimax-m3 | Volcengine | URL直传 |
| 4 | agnes-2.0-flash | apihub.agnes-ai.com | URL直传 |

审计输出字段：`has_brand_name`, `has_logo`, `has_watermark`, `has_chinese_text`, **`has_text`**（所有文字含英文）, `text_type`, `is_promo_banner`, `needs_cleaning`, `weight_kg`, `length_cm`, `width_cm`, `height_cm`

## 翻译（2层回退）

1. Kimi moonshot-v1-8k（越南语翻译专家 prompt）
2. minimax-m3 via Volcengine

翻译内容：标题(B)、变种属性名(G/I/K)、变种属性值(H/J/L)、描述文字(C)。

规则见 `references/vietnamese-style.md`：品类名词开头 ≤80 字符、品牌词改 `phù hợp với`、删原装/原厂。

## 确定性清洗规则

- 品牌 → 留空
- 库存 → 30
- SKU → `YYYYMMDD00001`
- 视频 → 删除
- 图片 URL → 统一 https
- 价格列 → 改名「本地展示价」（只删空列）
- 列映射 → 根据列头名称动态定位，兼容不同 TikTok 导出格式

## 图像分类规则

**描述列（C）图片：**
- URL 模式匹配促销/服务图 → `delete`（paybtn, kefu, coupon, ibay365, itemtplimg 等）
- 视觉审计 `is_promo_banner: true` → `delete`
- 有品牌/logo/水印/文字（中/英） → `regen`（翻译越南语+去品牌）
- 干净产品图 → `keep`

**主图/附图/变种图：绝不删除，只 regen 或 keep**

## 生图回退链

多 key 轮换 + 全局重试池（失败自动重试 2 轮）：

`edits (gpt-image-2) → nano-banana-2(4K) → 豆包 seedream(2K) → GPT generations(1K)`

## 飞书表格字段

表格需配置字段和 AI 字段捷径：

| 字段 | 类型 | 作用 |
|------|------|------|
| 附件链接 | text | 接收原始图片 URL |
| 链接转附件 | attachment | AI：URL→附件 |
| 生成图片 | attachment | AI：清洗+翻译 |
| 图片转链接 | text | AI：附件→URL（拉取用） |

## 硬性约束

- `delete` 仅对 C 列（描述）图片生效。主图/附图/变种图绝不删除。
- 不同 TikTok 导出表格列顺序可能不同，代码根据列头名称动态定位。
- 图片 URL 约 24 小时过期（OSS 签名），需尽快处理。
- `gw.alicdn.com` 图片防盗链，需多 UA/Referer 重试下载转 base64。
- Excel 锁：`wb.save()` 等 10 次重试，失败存 `_final` 后缀文件。

## 评测

```bash
python tkvn.py eval
```

黄金用例在 `evals/` 目录下（case1-5）。
