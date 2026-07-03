# TK VN Product Sheet Skill

处理中国来源的 TikTok 商品表格，自动生成越南站可用的刊登表格。

## 默认工作流

CLI 入口（推荐）：`python tkvn.py <command> ...`

等价脚本命令见下方。

### 全自动模式（推荐）

```bash
python tkvn.py process "input.xlsx" \
  --hfsy-key $HFSY_API_KEY \
  --doubao-key $ARK_API_KEY \
  --agnes-key $AGNES_API_KEY
# 或直接用环境变量: python tkvn.py process "input.xlsx"
```

一条命令完成：准备 → 翻译 → 视觉审计 → 生图清洗 → 写回。

### 分步模式

```bash
# 1. 准备（只读，输出 work.json）
python tkvn.py prepare "input.xlsx"
# 或: python scripts/run_pipeline.py prepare "input.xlsx" work.json

# 2. 人工或 agent 填写 work.json（翻译结果、图像决策）

# 3. 写回表格
python tkvn.py finalize "input.xlsx" work.json "output.xlsx"
# 或: python scripts/run_pipeline.py finalize "input.xlsx" work.json "output.xlsx"
```

### 文件夹监听模式

```bash
python tkvn.py watch
# 或: python scripts/watch.py
```

## 确定性清洗规则

- 品牌列（D）→ 留空
- 库存（Q列）→ 30
- SKU → `YYYYMMDD00001` 格式
- 视频链接 → 删除
- 图片 URL → 统一 `https://`
- 价格列 → 改名「本地展示价」
- 35 列格式对齐

## 图像规则

- **主图/附图/变种图**：检测品牌名、logo、水印 → 用生图模型清洗（不删除）
- **描述（C列）图片**：删除无关促销图，清洗产品图
- 生图回退链：`edits → nano-banana-2(4K) → 豆包(2K) → GPT generations(1K)`
- 视觉审计模型：`minimax-m3`（火山端点）首选，`agnes-2.0-flash` 备选

## 验证

```bash
python tkvn.py check "output.xlsx" brand_set
# 或: python scripts/check_sheet.py "output.xlsx" brand_set
```

## 硬性约束

- `delete` 仅对 C 列（描述）图片生效。主图/附图/变种图绝不删除。
- 生图无像素级 mask inpaint，去水印/logo 是尽力而为。
- 图片 URL 约 24 小时过期，需尽快上传 TikTok。
- `gw.alicdn.com` 图片常被 API 拒绝（403/400），需下载转 base64。
- Excel 锁：目标 xlsx 被 Excel 打开时 `wb.save()` 报 PermissionError。
- 生图慢（每张 30-60s），用 batch_process 并发或后台跑。

## 评测

```bash
python tkvn.py eval
# 或: python scripts/run_evals.py
```

黄金用例在 `evals/` 目录下（case1-5）。
