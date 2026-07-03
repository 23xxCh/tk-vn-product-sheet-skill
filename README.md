# tk-vn-product-sheet-skill

TikTok 越南站商品表格自动化处理工具。从淘宝/天猫中文商品表格出发，经过去品牌、翻译越南语、图像清洗，生成可直接刊登的表格。

## 快速开始

使用 CLI 入口（推荐）：

```bash
pip install openpyxl

python tkvn.py process "0630-tk.xlsx" \
  --hfsy-key $HFSY_API_KEY \
  --doubao-key $ARK_API_KEY \
  --agnes-key $AGNES_API_KEY
```

等价脚本命令：`python scripts/batch_process.py "0630-tk.xlsx" ...`

## 分步使用

```bash
# CLI（推荐）
python tkvn.py prepare "input.xlsx"
# 编辑 work.json
python tkvn.py finalize "input.xlsx" work.json "output.xlsx"

# 或直接用脚本
python scripts/run_pipeline.py prepare "input.xlsx" work.json
python scripts/run_pipeline.py finalize "input.xlsx" work.json "output.xlsx"
```

## 验证

```bash
python tkvn.py check "output.xlsx" brand_set
# 或: python scripts/check_sheet.py "output.xlsx" brand_set
```

## 环境变量

```bash
HFSY_API_KEY=xxx    # 生图 API (nano-banana-2, GPT-Image-2)
ARK_API_KEY=xxx     # 翻译 + 视觉审计 (minimax-m3, 豆包)
AGNES_API_KEY=xxx   # 视觉审计备选 (agnes-2.0-flash)
```

## 评测

```bash
python tkvn.py eval
# 或: python scripts/run_evals.py
```
