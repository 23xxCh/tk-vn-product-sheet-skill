"""CLI entry point for tk-vn-product-sheet-skill.

Usage:
  python tkvn.py process <xlsx> [--hfsy-key KEY] [--doubao-key KEY] [--agnes-key KEY] [--gen-size SIZE]
  python tkvn.py prepare <xlsx> [-o OUT] [--stock N] [--sku-prefix DATE] [--drop-from-col N]
  python tkvn.py finalize <xlsx> <work.json> <out.xlsx>
  python tkvn.py watch [--input DIR] [--output DIR] [--interval SECS]
  python tkvn.py check <xlsx> <CHECK_NAME>
  python tkvn.py eval

Commands:
  process   全自动流水线 (prepare + translate + audit + gen + finalize)
  prepare   仅确定性清洗（品牌/库存/SKU/URL归一）
  finalize  写回 work.json 的结果到表格
  watch     文件夹监听自动处理
  check     校验输出结果
  eval      运行评测

Environment variables (fallback for --*-key):
  HFSY_API_KEY  生图 API (nano-banana-2, GPT-Image-2)
  ARK_API_KEY   翻译 + 视觉审计 (minimax-m3, 豆包)
  AGNES_API_KEY 视觉审计备选 (agnes-2.0-flash)
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

_SCRIPT_DIR = str(Path(__file__).resolve().parent / "scripts")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def cmd_process(args: argparse.Namespace) -> int:
    mod = importlib.import_module("batch_process")
    gen_workers = args.workers if hasattr(args, 'workers') and args.workers > 0 else 0
    argv = [
        args.xlsx,
        "--doubao-key", args.doubao_key,
        "--hfsy-key", args.hfsy_key,
        "--agnes-key", args.agnes_key,
        "--gen-size", args.gen_size,
        "--gen-workers", str(gen_workers),
    ]
    checkpoint = getattr(args, 'checkpoint', None)
    if checkpoint:
        argv += ["--checkpoint", checkpoint]
    if getattr(args, 'no_gen', False):
        argv += ["--no-gen"]
    return mod.main(argv)


def cmd_prepare(args: argparse.Namespace) -> int:
    mod = importlib.import_module("prepare_feishu_import")
    argv = [args.xlsx]
    if args.output:
        argv += ["-o", args.output]
    if args.stock:
        argv += ["--stock", str(args.stock)]
    if args.sku_prefix:
        argv += ["--sku-prefix", args.sku_prefix]
    if args.drop_from_col is not None:
        argv += ["--drop-from-col", str(args.drop_from_col)]
    return mod.main(argv)


def cmd_finalize(args: argparse.Namespace) -> int:
    mod = importlib.import_module("run_pipeline")
    return mod.main(["finalize", args.xlsx, args.work, args.out])


def cmd_watch(args: argparse.Namespace) -> int:
    mod = importlib.import_module("watch")
    argv = []
    if args.input:
        argv += ["--input", args.input]
    if args.output:
        argv += ["--output", args.output]
    if args.interval:
        argv += ["--interval", str(args.interval)]
    argv += ["--doubao-key", args.doubao_key]
    argv += ["--hfsy-key", args.hfsy_key]
    argv += ["--agnes-key", args.agnes_key]
    return mod.main(argv)


def cmd_check(args: argparse.Namespace) -> int:
    mod = importlib.import_module("check_sheet")
    return mod.main([args.xlsx, args.check])


def cmd_eval(_: argparse.Namespace) -> int:
    mod = importlib.import_module("run_evals")
    return mod.main([])


def cmd_push_regen(args: argparse.Namespace) -> int:
    mod = importlib.import_module("push_regen_to_feishu")
    argv = [args.work_json, "--base-token", args.base_token, "--table-id", args.table_id]
    if args.field:
        argv += ["--field", args.field]
    if args.include_skus:
        argv += ["--include-skus"]
    argv += ["--as", args.as_identity]
    return mod.main(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tkvn",
        description="TikTok Shop Vietnam product sheet processor",
        add_help=True,
    )
    sub = parser.add_subparsers(dest="cmd")

    # process
    p = sub.add_parser("process", help="全自动流水线")
    p.add_argument("xlsx")
    p.add_argument("--hfsy-key", default=os.environ.get("HFSY_API_KEY", ""),
                   help="HFSy API key(s), comma-separated for rotation")
    p.add_argument("--doubao-key", default=os.environ.get("ARK_API_KEY", ""),
                   help="Doubao/minimax-m3 key(s), comma-separated for rotation")
    p.add_argument("--agnes-key", default=os.environ.get("AGNES_API_KEY", ""),
                   help="Agnes vision key(s), comma-separated for rotation")
    p.add_argument("--gen-size", default="4K", choices=["1K", "2K", "4K"])
    p.add_argument("--workers", type=int, default=0,
                   help="Gen workers (0=auto, default min(50, CPU*2))")
    p.add_argument("--checkpoint", default=None,
                   help="Checkpoint file for resume support")
    p.add_argument("--no-gen", action="store_true",
                   help="跳过本地生图,输出work.json供飞书AI字段快捷方式处理")
    p.set_defaults(fn=cmd_process)

    # prepare
    p = sub.add_parser("prepare", help="仅确定性清洗")
    p.add_argument("xlsx")
    p.add_argument("-o", "--output")
    p.add_argument("--stock", type=int)
    p.add_argument("--sku-prefix")
    p.add_argument("--drop-from-col", type=int)
    p.set_defaults(fn=cmd_prepare)

    # finalize
    p = sub.add_parser("finalize", help="写回 work.json 结果")
    p.add_argument("xlsx")
    p.add_argument("work")
    p.add_argument("out")
    p.set_defaults(fn=cmd_finalize)

    # watch
    p = sub.add_parser("watch", help="文件夹监听自动处理")
    p.add_argument("--input")
    p.add_argument("--output")
    p.add_argument("--interval", type=int)
    p.add_argument("--doubao-key", default=os.environ.get("ARK_API_KEY", ""))
    p.add_argument("--hfsy-key", default=os.environ.get("HFSY_API_KEY", ""))
    p.add_argument("--agnes-key", default=os.environ.get("AGNES_API_KEY", ""))
    p.set_defaults(fn=cmd_watch)

    # check
    p = sub.add_parser("check", help="校验输出结果")
    p.add_argument("xlsx")
    p.add_argument("check", choices=["brand_set", "stock_set", "video_cleared", "sku_format", "image_urls_https"])
    p.set_defaults(fn=cmd_check)

    # eval
    sub.add_parser("eval", help="运行评测").set_defaults(fn=cmd_eval)

    # push-regen
    p = sub.add_parser("push-regen", help="推送需重新生成的图片URL到飞书多维表格")
    p.add_argument("work_json", help="work.json 路径")
    p.add_argument("--base-token", required=True, help="飞书 Base token")
    p.add_argument("--table-id", required=True, help="飞书表格 ID")
    p.add_argument("--field", default="附件链接", help="接收URL的字段名 (默认: 附件链接)")
    p.add_argument("--include-skus", action="store_true", help="同时写入 SKU 和列信息")
    p.add_argument("--as", dest="as_identity", default="user", choices=["user", "bot"])
    p.set_defaults(fn=cmd_push_regen)

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0

    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
