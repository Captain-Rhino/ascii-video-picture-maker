#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把静态图片转成 ASCII / 数字字符图。

支持单图和批量目录输入。

用法示例：
1) 单张图片输出为 PNG
python image_2_ascii.py --input input.jpg --output out.png

2) 单张图片输出为文本
python image_2_ascii.py --input input.jpg --output out.txt

3) 批量处理文件夹内图片
python image_2_ascii.py --input images --output ascii_out

4) 纯数字风格
python image_2_ascii.py --input input.jpg --output out.png --mode digits

5) 调整清晰度
python image_2_ascii.py --input input.jpg --output out.png --cols 160

依赖：
pip install opencv-python pillow numpy
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ASCII_CHARSET = "@%#*+=-:. "
DIGIT_CHARSET = "9876543210"
PIL_RESAMPLING = getattr(Image, "Resampling", Image)
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


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

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def parse_resolution(value, src_w, src_h):
    """解析输出分辨率；默认跟原图一致。"""
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


def load_image(path):
    """读取图片并统一成 RGB numpy 数组。"""
    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) > 1:
            print(f"[WARN] {path.name} 是动图格式，这里先处理第一帧；后续可再扩展成逐帧导出。")
        image.seek(0)
        return np.array(image.convert("RGB"))


def frame_to_ascii(gray_frame, cols, charset, output_aspect_ratio=None):
    """把灰度图映射成字符矩阵。"""
    h, w = gray_frame.shape
    aspect_ratio = output_aspect_ratio if output_aspect_ratio is not None else (h / w)
    rows = max(1, int(aspect_ratio * cols * 0.55))

    resized = cv2.resize(gray_frame, (cols, rows), interpolation=cv2.INTER_AREA)

    num_chars = len(charset)
    idx = (resized.astype(np.float32) / 255.0 * (num_chars - 1)).astype(np.int32)
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


def build_output_path(source_path, output_path, output_format):
    if output_path is not None:
        return Path(output_path)

    suffix = ".txt" if output_format == "text" else ".png"
    return source_path.with_name(f"{source_path.stem}_ascii{suffix}")


def detect_output_format(output_path, explicit_format):
    if explicit_format:
        return explicit_format

    suffix = output_path.suffix.lower()
    if suffix in {".txt", ".md", ".asc"}:
        return "text"
    return "image"


def collect_input_files(input_path, recursive=False):
    if input_path.is_file():
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"输入路径不存在：{input_path}")

    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    files = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES]
    files.sort()
    return files


def save_text_output(output_path, ascii_text):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ascii_text + "\n", encoding="utf-8")


def save_image_output(output_path, rgb_img):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bgr_img = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(str(output_path), bgr_img):
        raise RuntimeError(f"写入图片失败：{output_path}")


def process_single_image(input_path, output_path, args, font):
    rgb_frame = load_image(input_path)
    src_h, src_w = rgb_frame.shape[:2]
    out_w, out_h = parse_resolution(args.resolution, src_w, src_h)
    target_size = (out_w, out_h)
    output_aspect_ratio = out_h / out_w

    gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)

    charset = ASCII_CHARSET if args.mode == "ascii" else DIGIT_CHARSET
    if args.invert:
        charset = charset[::-1]

    ascii_text, rows = frame_to_ascii(gray, args.cols, charset, output_aspect_ratio=output_aspect_ratio)
    output_format = detect_output_format(output_path, args.format)

    print(f"[INFO] 输入文件: {input_path}")
    print(f"[INFO] 输出文件: {output_path}")
    print(f"[INFO] 输出格式: {output_format}")
    print(f"[INFO] 输出尺寸: {out_w}x{out_h}")

    if output_format == "text":
        save_text_output(output_path, ascii_text)
        print(f"[DONE] 已输出 ASCII 文本: {output_path}")
        return

    rgb_img = render_ascii_to_image(
        ascii_text,
        args.cols,
        rows,
        font,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
        target_size=target_size,
    )
    save_image_output(output_path, rgb_img)
    print(f"[DONE] 已输出 ASCII 图片: {output_path}")


def process_batch_images(input_dir, output_dir, args, font):
    input_files = collect_input_files(input_dir, recursive=args.recursive)
    if not input_files:
        raise RuntimeError(f"目录中未找到可处理的图片：{input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_format = args.format or "image"
    suffix = ".txt" if output_format == "text" else ".png"

    print(f"[INFO] 输入目录: {input_dir}")
    print(f"[INFO] 输出目录: {output_dir}")
    print(f"[INFO] 图片数量: {len(input_files)}")

    for index, source_path in enumerate(input_files, start=1):
        target_path = output_dir / f"{source_path.stem}_ascii{suffix}"
        process_single_image(source_path, target_path, args, font)
        print(f"[INFO] 已完成 {index}/{len(input_files)}: {source_path.name}")


def parse_args():
    parser = argparse.ArgumentParser(description="把静态图片转成 ASCII / 数字字符图。")
    parser.add_argument("--input", required=True, help="输入图片路径，或包含图片的目录")
    parser.add_argument("--output", default=None, help="输出文件路径，或批量模式下的输出目录")
    parser.add_argument(
        "--format",
        choices=["image", "text"],
        default=None,
        help="输出格式：image=图片，text=文本；默认根据输出后缀自动判断",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="source",
        help="输出分辨率：source 或 WIDTHxHEIGHT，例如 1280x720",
    )
    parser.add_argument("--cols", type=int, default=120, help="字符列数，越大越清楚但越慢")
    parser.add_argument("--font_size", type=int, default=12, help="字体大小")
    parser.add_argument("--font", type=str, default=None, help="等宽字体路径，可留空自动寻找")
    parser.add_argument(
        "--mode",
        choices=["ascii", "digits"],
        default="ascii",
        help="ascii=常规字符画；digits=纯数字风格",
    )
    parser.add_argument("--invert", action="store_true", help="反转明暗映射")
    parser.add_argument("--recursive", action="store_true", help="批量模式下递归扫描子目录")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在：{input_path}")

    font_path = find_mono_font(args.font)
    if font_path:
        font = ImageFont.truetype(font_path, args.font_size)
        print(f"[INFO] 使用字体: {font_path}")
    else:
        font = ImageFont.load_default()
        print("[WARN] 没找到等宽字体，已回退到 PIL 默认字体。效果可能一般。")

    if input_path.is_file():
        output_path = build_output_path(input_path, Path(args.output).expanduser().resolve() if args.output else None, args.format)
        if output_path.resolve() == input_path.resolve():
            raise ValueError("--output 不能与 --input 相同，请使用新的输出文件名")
        process_single_image(input_path, output_path, args, font)
        return

    if not input_path.is_dir():
        raise FileNotFoundError(f"输入路径不存在：{input_path}")

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    else:
        output_dir = input_path.parent / f"{input_path.name}_ascii"

    if output_dir.resolve() == input_path.resolve():
        raise ValueError("批量模式下输出目录不能与输入目录相同，请指定新的输出目录。")

    process_batch_images(input_path, output_dir, args, font)


if __name__ == "__main__":
    main()