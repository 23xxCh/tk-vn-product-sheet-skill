# AGENTS.md - tk-vn-product-sheet-skill

## 两种工作流

### 飞书模式（推荐）

```bash
python tkvn.py process "input.xlsx" --kimi-key $KIMI_API_KEY --no-gen
python tkvn.py push-regen work_auto.json -t <token> -i <table>
# 飞书 AI 字段捷径处理图片后
python tkvn.py pull-regen work_auto.json -t <token> -i <table>
python tkvn.py finalize "input.xlsx" work_auto.json "output.xlsx"
```

### 本地生图模式

```bash
python tkvn.py process "input.xlsx" \
  --kimi-key $KIMI_API_KEY --hfsy-key "K1,K2" --workers 50
```

## 关键文件

- `tkvn.py` — CLI 统一入口
- `scripts/batch_process.py` — 全自动流水线核心
- `scripts/run_pipeline.py` — 分步编排（prepare/finalize）
- `scripts/sheet_io.py` — 列映射（动态头检测）
- `scripts/push_regen_to_feishu.py` — 推送 URL 到飞书
- `scripts/pull_regen_from_feishu.py` — 从飞书拉取新 URL
- `scripts/check_sheet.py` — 校验
- `references/vietnamese-style.md` — 翻译规范
- `references/image-rules.md` — 图像分类规则
- `references/field-mapping.md` — 列映射参考

## 视觉审计

4 层回退：Kimi → 百炼 Qwen-VL → minimax-m3 → agnes-2.0-flash

## 验证

```bash
python tkvn.py check "output.xlsx" brand_set
python tkvn.py check "output.xlsx" sku_format
python tkvn.py eval
```
