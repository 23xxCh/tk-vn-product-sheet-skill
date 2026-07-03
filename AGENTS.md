# AGENTS.md - tk-vn-product-sheet-skill

## 用途

处理 TikTok 越南站商品表格：确定性清洗 + AI 翻译 + 图像清洗。

## 默认工作流

```bash
python scripts/batch_process.py "<xlsx>" --hfsy-key $HFSY_API_KEY --doubao-key $ARK_API_KEY --agnes-key $AGNES_API_KEY
```

## 分步工作流

```bash
python scripts/run_pipeline.py prepare "<xlsx>" work.json
# 编辑 work.json
python scripts/run_pipeline.py finalize "<xlsx>" work.json "output.xlsx"
```

## 验证

```bash
python scripts/check_sheet.py "output.xlsx" brand_set
python scripts/check_sheet.py "output.xlsx" stock_set
python scripts/check_sheet.py "output.xlsx" video_cleared
python scripts/check_sheet.py "output.xlsx" sku_format
python scripts/check_sheet.py "output.xlsx" image_urls_https
```
