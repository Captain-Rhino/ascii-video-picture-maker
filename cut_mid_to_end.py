#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从视频的指定时间区间截取片段，并保留音频同步。

默认从 24 秒开始截到结尾；如果指定 --end，则会截取到该秒数为止。

用法示例：
python cut_24_to_end.py --input input.mp4
python cut_24_to_end.py --input input.mp4 --output my_cut.mp4
python cut_24_to_end.py --input input.mp4 --start 24 --end 60
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_START_SECONDS = 24.0
DEFAULT_OUTPUT_NAME = "24_to_endtime_cut.mp4"


def ensure_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("未找到 ffmpeg，请先安装 ffmpeg 并确保它已加入 PATH。")
    return ffmpeg_path


def has_audio_stream(ffprobe_path: str, input_path: Path) -> bool:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffprobe 读取音频流信息失败：\n" + (result.stderr.strip() or result.stdout.strip())
        )
    return bool(result.stdout.strip())


def format_seconds_for_name(value: float) -> str:
    text = f"{value:g}"
    return text.replace(".", "p")


def default_output_name(start_seconds: float, end_seconds: float | None) -> str:
    if end_seconds is None:
        return DEFAULT_OUTPUT_NAME if start_seconds == DEFAULT_START_SECONDS else f"{format_seconds_for_name(start_seconds)}_to_endtime_cut.mp4"
    return f"{format_seconds_for_name(start_seconds)}_to_{format_seconds_for_name(end_seconds)}_cut.mp4"


def build_command(
    ffmpeg_path: str,
    input_path: Path,
    output_path: Path,
    start_seconds: float,
    end_seconds: float | None,
    keep_audio: bool,
) -> list[str]:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"trim=start={start_seconds}" + (f":end={end_seconds}" if end_seconds is not None else "") + ",setpts=PTS-STARTPTS",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]

    if keep_audio:
        command.extend([
            "-af",
            f"atrim=start={start_seconds}" + (f":end={end_seconds}" if end_seconds is not None else "") + ",asetpts=PTS-STARTPTS",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ])

    command.append(str(output_path))
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从视频指定时间区间截取片段，并同步保留音频。")
    parser.add_argument("--input", required=True, help="输入视频路径")
    parser.add_argument(
        "--output",
        default=None,
        help="输出视频路径；默认按起止时间自动生成文件名",
    )
    parser.add_argument(
        "--start",
        type=float,
        default=DEFAULT_START_SECONDS,
        help=f"截取起始时间（秒），默认 {DEFAULT_START_SECONDS}",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=None,
        help="截取结束时间（秒）；不填则截到视频结尾",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在：{input_path}")

    if args.end is not None and args.end <= args.start:
        raise ValueError("--end 必须大于 --start")

    output_path = Path(args.output).expanduser().resolve() if args.output else Path.cwd() / default_output_name(args.start, args.end)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.resolve() == input_path.resolve():
        raise ValueError("输出文件不能与输入文件相同，请指定新的输出文件名。")

    ffmpeg_path = ensure_ffmpeg()
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise RuntimeError("未找到 ffprobe，请先安装 ffmpeg 完整套件并确保 ffprobe 可用。")

    audio_exists = has_audio_stream(ffprobe_path, input_path)
    command = build_command(ffmpeg_path, input_path, output_path, args.start, args.end, audio_exists)

    print(f"[INFO] 输入文件: {input_path}")
    print(f"[INFO] 输出文件: {output_path}")
    print(f"[INFO] 起始时间: {args.start} 秒")
    print(f"[INFO] 结束时间: {args.end if args.end is not None else '视频结尾'}")
    print(f"[INFO] 音频轨道: {'存在，将同步保留' if audio_exists else '未检测到，输出仅保留视频'}")

    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 截取失败，请检查输入视频和 ffmpeg 安装是否正常。")

    print("[INFO] 截取完成。")


if __name__ == "__main__":
    main()