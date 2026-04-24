# ascii_video_meme

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![Status](https://img.shields.io/badge/Status-Working-brightgreen)](#)

把普通视频变成 ASCII 或数字字符风格的视频。  
这个项目目前是一个轻量的本地工具链：先裁剪素材，再做字符化渲染，最后输出可分享的视频结果（可自动保留音频）。

## Why This Project

很多 ASCII 视频工具要么效果单一，要么导出流程比较重。这个仓库的目标很简单：

1. 本地直接跑，不依赖复杂服务。
2. 参数足够直观，能快速试出风格。
3. 同时保留剪辑和渲染两步，方便做视频二创。

## Features

- 视频转 ASCII 字符风格。
- 视频转纯数字流风格。
- 图片转 ASCII 字符图。
- 批量图片转 ASCII。
- 可控制列数、分辨率、帧率、字体、明暗反转。
- 自动尝试保留原音频（依赖 ffmpeg）。
- 支持从任意时间区间裁剪视频片段。
- 输入无音轨时自动降级为无音频输出。

## Project Structure

- [video_to_ascii.py](video_to_ascii.py): 视频逐帧转字符视频，并可自动合并原音频。
- [image_2_ascii.py](image_2_ascii.py): 单图或批量图片转字符图，支持导出图片或文本。
- [cut_mid_to_end.py](cut_mid_to_end.py): 按起止时间裁剪视频，保持音视频同步。
- [new.html](new.html): WebGL 实时字符流实验页（本地浏览器可直接打开）。
- [what to improve.md](what%20to%20improve.md): 后续迭代方向草案。

## Requirements

### Python

- Python 3.10+
- 依赖包：opencv-python, pillow, numpy

安装命令：

```bash
pip install opencv-python pillow numpy
```

### System Tools

- ffmpeg
- ffprobe

请确保 ffmpeg 和 ffprobe 都已加入系统 PATH。

## Quick Start

### 1) 裁剪视频片段

从 24 秒裁到结尾：

```bash
python cut_mid_to_end.py --input input.mp4
```

指定输出文件名：

```bash
python cut_mid_to_end.py --input input.mp4 --output my_cut.mp4
```

按区间裁剪（例如 24 到 60 秒）：

```bash
python cut_mid_to_end.py --input input.mp4 --start 24 --end 60
```

### 2) 转成 ASCII 视频

基础用法：

```bash
python video_to_ascii.py --input input.mp4 --output ascii_out.mp4
```

数字流风格：

```bash
python video_to_ascii.py --input input.mp4 --output digit_out.mp4 --mode digits
```

提高字符细节：

```bash
python video_to_ascii.py --input input.mp4 --output out.mp4 --cols 160
```

自定义输出分辨率：

```bash
python video_to_ascii.py --input input.mp4 --output out.mp4 --resolution 1280x720
```

导出无音频版本：

```bash
python video_to_ascii.py --input input.mp4 --output out.mp4 --no-audio
```

### 3) 转成 ASCII 图片

单张图片输出为 ASCII 图片：

```bash
python image_2_ascii.py --input input.jpg --output out.png
```

单张图片输出为文本：

```bash
python image_2_ascii.py --input input.jpg --output out.txt
```

批量处理文件夹内图片：

```bash
python image_2_ascii.py --input images --output ascii_out
```

## Common Workflow

推荐顺序：

1. 先用 cut_mid_to_end.py 切出目标片段。
2. 再把片段交给 video_to_ascii.py 做字符化导出。

这个流程比较适合短视频二创、片段混剪、终端风动态背景制作。

## Parameters (video_to_ascii.py)

- --input: 输入视频路径。
- --output: 输出视频路径。
- --resolution: 输出分辨率，source 或 WIDTHxHEIGHT。
- --cols: 字符列数，越大越清晰，速度越慢。
- --fps: 输出帧率，默认跟随原视频。
- --font_size: 字体大小。
- --font: 字体路径，可留空自动寻找。
- --mode: ascii 或 digits。
- --invert: 反转明暗映射。
- --no-audio: 不合并原音频。

## Parameters (cut_mid_to_end.py)

- --input: 输入视频路径。
- --output: 输出视频路径，不填则自动命名。
- --start: 起始秒数，默认 24。
- --end: 结束秒数，不填则截到结尾。

## Troubleshooting

- 报错找不到 ffmpeg 或 ffprobe：确认已安装并加入 PATH。
- 输出没有声音：先确认输入视频本身有音轨，再确认本机 ffmpeg 可用。
- 渲染很慢：降低 cols 或输出分辨率。
- 字符比例看着不对：调整 font_size、cols、resolution 的组合。

## Roadmap

后续方向已整理在 [what to improve.md](what%20to%20improve.md)，包括：

- 图片与动图支持
- 彩色 ASCII 模式
- 编码体积控制
- 随机风格模式
- 预设系统与一键工作流
- 性能优化与 GPU 路线

## Contributing

欢迎提 Issue 和 PR。  
如果你想贡献代码，建议优先从这几类问题入手：

1. 参数体验和默认值优化。
2. 导出速度与体积控制。
3. 新的字符映射或主题风格。

## License

MIT
