#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把普通视频转成 ASCII / 数字字符视频（默认自动保留原音频）

用法示例：
1) 普通 ASCII 字符效果
python video_to_ascii.py --input input.mp4 --output ascii_out.mp4

2) 纯数字风格（更像“数字流”）
python video_to_ascii.py --input input.mp4 --output digit_out.mp4 --mode digits

3) 调整清晰度（cols 越大越清楚，但越慢）
python video_to_ascii.py --input input.mp4 --output out.mp4 --cols 160

4) 自定义输出分辨率
python video_to_ascii.py --input input.mp4 --output out.mp4 --resolution 1280x720

5) 如需只导出无音频视频
python video_to_ascii.py --input input.mp4 --output out.mp4 --no-audio

依赖：
pip install opencv-python pillow numpy
如需自动合并音频，请确保系统已安装 ffmpeg
"""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ASCII_CHARSET = "@%#*+=-:. "
DIGIT_CHARSET = "9876543210"
PIL_RESAMPLING = getattr(Image, "Resampling", Image)


def find_mono_font(user_font_path=None):
    """尽量自动找一个等宽字体。"""
    candidates = []

    if user_font_path:
        candidates.append(user_font_path)

    if os.name == "nt":
        candidates += [
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\cour.ttf",
            r"C:\Windows\Fonts\lucon.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        ]

    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def parse_resolution(value, src_w, src_h):
    """解析输出分辨率；默认跟原视频一致。"""
    normalized = (value or "source").strip().lower()
    if normalized in {"source", "original", "input"}:
        return src_w, src_h

    match = re.fullmatch(r"(\d+)[xX](\d+)", value.strip())
    if not match:
        raise ValueError("--resolution 必须是 source 或 WIDTHxHEIGHT，例如 1280x720")

    out_w = int(match.group(1))
    out_h = int(match.group(2))
    if out_w <= 0 or out_h <= 0:
        raise ValueError("--resolution 的宽高必须是正整数")

    return out_w, out_h


def build_silent_output_path(output_path):
    """为中间无声视频生成一个临时文件名。"""
    return output_path.with_name(f"{output_path.stem}.silent_tmp{output_path.suffix}")


def merge_audio_with_ffmpeg(silent_video_path, input_path, output_path):
    """使用 ffmpeg 将原视频音频合并到导出视频中。"""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("[WARN] 未找到 ffmpeg，无法自动合并音频，将保留无音频输出。")
        return False

    cmd = [
        ffmpeg_path,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(silent_video_path),
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("[WARN] ffmpeg 合并音频失败，将保留无音频输出。")
        if result.stderr:
            error_tail = "\n".join(result.stderr.strip().splitlines()[-8:])
            if error_tail:
                print(error_tail)
        return False

    print("[INFO] 已完成音频合并；如果原视频含音轨，输出文件已自动带上。")
    return True


def frame_to_ascii(gray_frame, cols, charset, output_aspect_ratio=None):
    """
    把灰度图映射成字符矩阵。
    返回：
        ascii_text: 多行字符串
        rows: 行数
    """
    h, w = gray_frame.shape

    # 用最终输出画布的宽高比来计算行数，避免导出分辨率变化后画面被拉伸。
    aspect_ratio = output_aspect_ratio if output_aspect_ratio is not None else (h / w)
    rows = max(1, int(aspect_ratio * cols * 0.55))

    resized = cv2.resize(gray_frame, (cols, rows), interpolation=cv2.INTER_AREA)

    num_chars = len(charset)
    # 亮度 [0,255] -> 字符索引 [0, num_chars-1]
    idx = (resized.astype(np.float32) / 255.0 * (num_chars - 1)).astype(np.int32)

    # 注意：暗处通常用更“密”的字符，所以这里不反转
    chars = np.array(list(charset))[idx]

    lines = ["".join(row.tolist()) for row in chars]
    ascii_text = "\n".join(lines)
    return ascii_text, rows


def render_ascii_to_image(
    ascii_text,
    cols,
    rows,
    font,
    fg=(255, 255, 255),
    bg=(0, 0, 0),
    target_size=None,
):
    """把字符文本渲染为一张 RGB 图。"""
    # 估计单字符尺寸
    bbox = font.getbbox("A")
    char_w = max(1, bbox[2] - bbox[0])
    char_h = max(1, bbox[3] - bbox[1] + 2)

    render_w = char_w * cols
    render_h = char_h * rows

    img = Image.new("RGB", (render_w, render_h), color=bg)
    draw = ImageDraw.Draw(img)
    draw.multiline_text((0, 0), ascii_text, font=font, fill=fg, spacing=0)

    if target_size and (render_w, render_h) != target_size:
        img = img.resize(target_size, resample=PIL_RESAMPLING.BICUBIC)

    return np.array(img)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="输入视频路径")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument(
        "--resolution",
        type=str,
        default="source",
        help="输出分辨率：source 或 WIDTHxHEIGHT，例如 1280x720",
    )
    parser.add_argument("--cols", type=int, default=120, help="字符列数，越大越清楚但越慢")
    parser.add_argument("--fps", type=float, default=None, help="输出帧率；默认跟原视频一致")
    parser.add_argument("--font_size", type=int, default=12, help="字体大小")
    parser.add_argument("--font", type=str, default=None, help="等宽字体路径，可留空自动寻找")
    parser.add_argument("--mode", choices=["ascii", "digits"], default="ascii",
                        help="ascii=常规字符画；digits=纯数字风格")
    parser.add_argument("--invert", action="store_true", help="反转明暗映射")
    parser.add_argument("--no-audio", action="store_true", help="不自动合并原视频音频")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("--output 不能与 --input 相同，请使用新的输出文件名")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    silent_output_path = build_silent_output_path(output_path) if not args.no_audio else output_path

    charset = ASCII_CHARSET if args.mode == "ascii" else DIGIT_CHARSET
    if args.invert:
        charset = charset[::-1]

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {input_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS)
    if not src_fps or src_fps <= 1e-6:
        src_fps = 25.0
    out_fps = args.fps or src_fps

    font_path = find_mono_font(args.font)
    if font_path:
        font = ImageFont.truetype(font_path, args.font_size)
        print(f"[INFO] 使用字体: {font_path}")
    else:
        font = ImageFont.load_default()
        print("[WARN] 没找到等宽字体，已回退到 PIL 默认字体。效果可能一般。")

    writer = None
    frame_count = 0
    target_size = None
    output_aspect_ratio = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if target_size is None:
            src_h, src_w = frame.shape[:2]
            out_w, out_h = parse_resolution(args.resolution, src_w, src_h)
            target_size = (out_w, out_h)
            output_aspect_ratio = out_h / out_w

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        ascii_text, rows = frame_to_ascii(gray, args.cols, charset, output_aspect_ratio=output_aspect_ratio)
        rgb_img = render_ascii_to_image(
            ascii_text,
            args.cols,
            rows,
            font,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            target_size=target_size,
        )

        bgr_img = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

        if writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(silent_output_path), fourcc, out_fps, target_size)
            if not writer.isOpened():
                raise RuntimeError("VideoWriter 初始化失败，请检查输出路径或编码器支持。")
            print(f"[INFO] 输出尺寸: {target_size[0]}x{target_size[1]}, FPS={out_fps}")

        writer.write(bgr_img)
        frame_count += 1

        if frame_count % 30 == 0:
            print(f"[INFO] 已处理 {frame_count} 帧...")

    cap.release()
    if writer is not None:
        writer.release()
    else:
        raise RuntimeError("未从输入视频中读取到任何帧，未生成输出文件。")

    if args.no_audio:
        print(f"[DONE] 已输出无音频视频: {output_path}")
        return

    if merge_audio_with_ffmpeg(silent_output_path, input_path, output_path):
        if silent_output_path.exists():
            silent_output_path.unlink()
        print(f"[DONE] 已输出带音频视频: {output_path}")
    else:
        silent_output_path.replace(output_path)
        print(f"[DONE] 自动合并音频未成功，已保留无音频视频: {output_path}")


if __name__ == "__main__":
    main()
