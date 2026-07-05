# tk-vn-product-sheet-skill

TikTok 越南站商品表格自动化处理工具。经过去品牌、翻译越南语、图像清洗，生成可直接刊登的表格。

## 快速开始

```bash
pip install openpyxl

# 飞书模式（推荐，生图委托飞书 AI 字段捷径）
python tkvn.py process "input.xlsx" --kimi-key $KIMI_API_KEY --no-gen
python tkvn.py push-regen work_auto.json --base-token <token> --table-id <table>
# 在飞书配置 AI 字段捷径处理图片后：
python tkvn.py pull-regen work_auto.json --base-token <token> --table-id <table>
python tkvn.py finalize "input.xlsx" work_auto.json "output.xlsx"

# 本地生图模式（全自动）
python tkvn.py process "input.xlsx" \
  --kimi-key $KIMI_API_KEY \
  --hfsy-key "key1,key2" \
  --workers 50
```

## CLI 命令

```bash
tkvn.py process     # 全自动流水线
  --kimi-key KEY    # Kimi 视觉审计+翻译（首选）
  --bailian-key KEY # 阿里云百炼 Qwen-VL（备用）
  --hfsy-key "K1,K2" # 多key逗号分隔轮换
  --no-gen          # 跳本地生图（飞书模式用）
  --workers N       # 生图并发数
  --checkpoint PATH # 断点续传

tkvn.py prepare     # 仅确定性清洗
tkvn.py finalize    # 写回 xlsx
tkvn.py push-regen  # 推送 regen URL 到飞书
tkvn.py pull-regen  # 从飞书拉取新 URL
tkvn.py watch       # 文件夹监听
tkvn.py check       # 校验
tkvn.py eval        # 评测
```

## 环境变量

```bash
KIMI_API_KEY=xxx     # Kimi 视觉审计+翻译（首选）
BAILIAN_API_KEY=xxx   # 百炼 Qwen-VL 视觉审计（备用，支持 URL 直传）
ARK_API_KEY=xxx       # minimax-m3 翻译 + 豆包生图
HFSY_API_KEY=xxx      # 生图 API，支持逗号分隔多 key
AGNES_API_KEY=xxx     # agnes-2.0-flash 视觉审计最后备用
```

## 视觉审计回退链

Kimi → 百炼 Qwen-VL → minimax-m3 → agnes-2.0-flash

## 依赖

- `openpyxl` — Excel 读写
- `requests` — HTTP 请求
- `lark-cli` — 飞书 CLI（仅飞书模式需要）
