# ascii_video_meme

这是一个把视频“变形”的小项目，核心有两个脚本：一个负责把普通视频转成 ASCII 或数字字符风格的视频，另一个负责从指定时间区间截取视频片段，并且保持音视频同步。

## 项目的有趣之处

这个目录里的两个脚本放在一起看，会很像一个“视频二创工作台”。你可以先用截取脚本把素材切到你想要的片段，再用 ASCII 脚本把这段视频变成字符画风格，得到一种介于复古终端和动态海报之间的视觉效果。

它有几个比较有意思的点：

1. 视频可以直接变成字符画，支持常规 ASCII 风格，也支持纯数字流风格。
2. 截取脚本支持从任意起始时间切到任意结束时间，或者只指定起始时间一直切到视频结尾，适合快速提取高能片段。
3. 两个脚本都尽量保留音频处理逻辑，输出结果不会只是“有画面没声音”的静态文件。
4. 整体实现很轻量，主要依赖 Python 和 ffmpeg，适合本地直接跑。

## 文件说明

- [video_to_ascii.py](video_to_ascii.py)：把视频逐帧转成 ASCII 或数字字符风格，并可自动合并原音频。
- [cut_24_to_end.py](cut_24_to_end.py)：从指定时间区间截取视频片段，默认从 24 秒开始截到结尾，也支持指定 `--end` 截到任意时间点。

## 运行依赖

### Python 包

安装以下依赖：

    pip install opencv-python pillow numpy

### 系统工具

需要安装 ffmpeg，并确保 ffmpeg 和 ffprobe 都已加入 PATH。

ffmpeg 用于视频编码、音频合并和时间截取；ffprobe 用于检测输入视频是否包含音轨。

## 运行方式

### 1. 截取视频从指定时间到结尾

默认会在当前目录生成 24_to_endtime_cut.mp4。

    python cut_24_to_end.py --input 你的原视频.mp4

如果你想自定义输出文件名：

    python cut_24_to_end.py --input 你的原视频.mp4 --output my_cut.mp4

如果你想改起始时间：

    python cut_24_to_end.py --input 你的原视频.mp4 --start 24

### 2. 截取视频从 x 秒到 y 秒

只要满足 `y > x`，就可以直接截取任意时间区间：

    python cut_24_to_end.py --input 你的原视频.mp4 --start 24 --end 60

如果不指定 `--output`，脚本会根据起止时间自动生成输出文件名，例如 `24_to_60_cut.mp4`。

### 3. 把视频转成 ASCII 字符视频

最基础的用法：

    python video_to_ascii.py --input input.mp4 --output ascii_out.mp4

纯数字风格：

    python video_to_ascii.py --input input.mp4 --output digit_out.mp4 --mode digits

提高字符列数，让画面更细腻：

    python video_to_ascii.py --input input.mp4 --output out.mp4 --cols 160

自定义输出分辨率：

    python video_to_ascii.py --input input.mp4 --output out.mp4 --resolution 1280x720

如果只想导出无音频版本：

    python video_to_ascii.py --input input.mp4 --output out.mp4 --no-audio

## 推荐工作流

如果你想先截素材，再做字符风格转换，可以按下面顺序来：

1. 先用 cut_24_to_end.py 从任意起止时间切出目标片段。
2. 再把生成的视频丢给 video_to_ascii.py，输出 ASCII 或数字字符版。

这样比较适合做短片段的二创、演示素材或者终端风格的视觉效果。

## 注意事项

- 输入视频路径需要真实存在。
- 如果系统里没有 ffmpeg，截取和音频合并都会失败。
- ASCII 视频对参数比较敏感，cols 越大越清晰，但速度也会更慢。
- 如果原视频没有音轨，脚本会自动输出无音频版本。