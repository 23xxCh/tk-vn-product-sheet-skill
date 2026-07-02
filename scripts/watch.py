"""Folder watcher — auto-process xlsx files dropped into a watched folder.

启动一次后常驻，轮询监听 input 文件夹。检测到新的 .xlsx 文件就自动跑完整
处理流程 (batch_process.py)，结果输出到 output 文件夹。用户只需把表格丢进
input 文件夹，无需任何提醒。

Usage:
  python scripts/watch.py                          # 用默认文件夹
  python scripts/watch.py --input ./input --output ./output
  python scripts/watch.py --interval 5             # 每5秒轮询一次

默认文件夹 (相对当前工作目录):
  ./tk_input/   ← 把待处理的 xlsx 丢这里
  ./tk_output/  ← 处理结果出现在这里
  ./tk_done/    ← 处理过的原文件移到这里 (避免重复处理)

零依赖 (只用标准库轮询, 不需要 watchdog)。跨平台。

按 Ctrl+C 停止。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch_process  # noqa: E402


def process_file(xlsx: Path, output_dir: Path, done_dir: Path,
                 ark_key: str, hfsy_key: str, agnes_key: str,
                 audit_workers: int, gen_workers: int, gen_size: str) -> None:
    """Process one xlsx: copy to output, run batch_process on the copy, move original to done."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_name = f"{xlsx.stem}_processed_{ts}.xlsx"
    out_path = output_dir / out_name

    print(f"\n{'='*55}", flush=True)
    print(f"检测到新文件: {xlsx.name}  →  处理中...", flush=True)
    print(f"{'='*55}", flush=True)

    # copy original to output first, process the copy (keeps input untouched)
    shutil.copy2(xlsx, out_path)
    try:
        report = batch_process.auto_process(
            str(out_path), ark_key, hfsy_key, agnes_key,
            work_path=str(output_dir / f"_work_{ts}.json"),
            audit_workers=audit_workers, gen_workers=gen_workers, gen_size=gen_size,
        )
        print(f"\n✅ 完成: {out_path.name}", flush=True)
        for k, v in report.items():
            print(f"   {k}: {v}", flush=True)
        # move original to done/ so it won't be reprocessed
        done_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(xlsx), str(done_dir / xlsx.name))
        print(f"   原文件已移至: {done_dir / xlsx.name}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ 处理失败: {xlsx.name}\n{e}", flush=True)
        traceback.print_exc()
        # leave original in place, remove partial output
        if out_path.exists():
            out_path.rename(output_dir / f"FAILED_{out_name}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Watch a folder and auto-process xlsx files")
    ap.add_argument("--input", default="./tk_input", help="watched input folder")
    ap.add_argument("--output", default="./tk_output", help="output folder")
    ap.add_argument("--done", default="./tk_done", help="processed originals folder")
    ap.add_argument("--interval", type=int, default=5, help="poll interval seconds")
    ap.add_argument("--doubao-key", default=os.environ.get("ARK_API_KEY", ""))
    ap.add_argument("--hfsy-key", default=os.environ.get("HFSY_API_KEY", ""))
    ap.add_argument("--agnes-key", default=os.environ.get("AGNES_API_KEY", ""))
    ap.add_argument("--audit-workers", type=int, default=12)
    ap.add_argument("--gen-workers", type=int, default=8)
    ap.add_argument("--gen-size", default="4K", choices=["1K", "2K", "4K"])
    args = ap.parse_args(argv)

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    done_dir = Path(args.done).resolve()
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== TK-VN 表格自动处理监听器 ===", flush=True)
    print(f"监听文件夹: {input_dir}", flush=True)
    print(f"输出文件夹: {output_dir}", flush=True)
    print(f"完成归档:   {done_dir}", flush=True)
    print(f"轮询间隔:   {args.interval}秒", flush=True)
    print(f"密钥: hfsyapi={'ok' if args.hfsy_key else '缺'} "
          f"Doubao={'ok' if args.doubao_key else '缺'} "
          f"Vision={'ok' if args.agnes_key else '缺'}", flush=True)
    if not args.hfsy_key and not args.doubao_key:
        print("⚠️ 未设置生图API密钥,图片不会被清洗。设置 HFSY_API_KEY 或 ARK_API_KEY。", flush=True)
    print(f"\n把 .xlsx 文件丢进 {input_dir.name}/ 就会自动处理。按 Ctrl+C 停止。\n", flush=True)

    seen: set[str] = set()
    # 忽略启动前已在文件夹里的临时/锁文件
    try:
        while True:
            for f in sorted(input_dir.glob("*.xlsx")):
                # 跳过Excel临时锁文件 ~$xxx.xlsx
                if f.name.startswith("~$"):
                    continue
                key = f.name
                if key in seen:
                    continue
                # 确认文件写入完成(大小稳定)
                size1 = f.stat().st_size
                time.sleep(1)
                if not f.exists():
                    continue
                if f.stat().st_size != size1:
                    continue  # 还在写入, 下轮再处理
                seen.add(key)
                process_file(f, output_dir, done_dir,
                             args.doubao_key, args.hfsy_key, args.agnes_key,
                             args.audit_workers, args.gen_workers, args.gen_size)
                print(f"\n继续监听 {input_dir.name}/ ...\n", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n监听已停止。", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
