"""CLI entry point for tk-vn-product-sheet-skill.

Usage:
  python tkvn.py preprocess <raw.xlsx> -o <clean.xlsx> [--dirty-manifest review.json]
  python tkvn.py process <xlsx> [--hfsy-key KEY] [--doubao-key KEY] [--agnes-key KEY] [--gen-size SIZE]
  python tkvn.py prepare <xlsx> [-o OUT] [--stock N] [--sku-prefix DATE] [--drop-from-col N]
  python tkvn.py finalize <xlsx> <work.json> <out.xlsx>
  python tkvn.py watch [--input DIR] [--output DIR] [--interval SECS]
  python tkvn.py check <xlsx> <CHECK_NAME>
  python tkvn.py eval

Commands:
  preprocess 原始表预处理（行内图片去重 + 描述脏数据清理）
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
        "--target-language", args.target_language,
        "--language-code", args.language_code,
    ]
    checkpoint = getattr(args, 'checkpoint', None)
    if checkpoint:
        argv += ["--checkpoint", checkpoint]
    return mod.main(argv)


def cmd_preprocess(args: argparse.Namespace) -> int:
    mod = importlib.import_module("preprocess_sheet")
    argv = [args.xlsx, "-o", args.output]
    if args.dirty_manifest:
        argv += ["--dirty-manifest", args.dirty_manifest]
    return mod.main(argv)


def cmd_prepare(args: argparse.Namespace) -> int:
    mod = importlib.import_module("run_pipeline")
    output = args.output or str(Path(args.xlsx).with_suffix(".work.json"))
    return mod.main(["run_pipeline.py", "prepare", args.xlsx, output])


def cmd_finalize(args: argparse.Namespace) -> int:
    mod = importlib.import_module("run_pipeline")
    return mod.main(["run_pipeline.py", "finalize", args.xlsx, args.work, args.out])


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
    return mod.main(["check_sheet.py", args.xlsx, args.check])


def cmd_eval(_: argparse.Namespace) -> int:
    mod = importlib.import_module("run_evals")
    return mod.main([])


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tkvn",
        description="TikTok Shop multilingual product sheet processor",
        add_help=True,
    )
    sub = parser.add_subparsers(dest="cmd")

    # preprocess
    p = sub.add_parser("preprocess", help="原始表预处理")
    p.add_argument("xlsx")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--dirty-manifest")
    p.set_defaults(fn=cmd_preprocess)

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
    p.add_argument("--target-language", default="Vietnamese",
                   help="Target language name, e.g. Vietnamese, Thai, English")
    p.add_argument("--language-code", default="vi",
                   help="BCP-47/short language code, e.g. vi, th, en")
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
    p.add_argument("check", choices=[
        "brand_set", "stock_set", "video_cleared", "sku_format",
        "image_urls_https", "duplicate_images", "required_fields", "final_integrity",
    ])
    p.set_defaults(fn=cmd_check)

    # eval
    sub.add_parser("eval", help="运行评测").set_defaults(fn=cmd_eval)

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0

    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
