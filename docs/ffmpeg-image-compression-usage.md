
# FFmpeg 图片压缩使用指南 (Image Compression)

本文是一份面向工程师的 FFmpeg 图片压缩与转换实用手册，旨在提供一页式速查指南，覆盖静态图片与图片序列处理的常见场景。

**目标读者与环境**

本指南适用于需要使用 FFmpeg 命令行工具进行图片处理的开发者和技术人员。示例命令在标准的 FFmpeg 环境下测试，请确保你的 FFmpeg 版本支持所需的编码器（如 `libwebp`, `libaom-av1` 等）。

## 快速上手

以下是几个最常用的图片处理命令，可以帮你快速开始。

- **将图片转换为另一种格式 (例如 PNG 转 JPEG):**
  ```bash
  ffmpeg -i input.png output.jpg
  ```
  *说明：FFmpeg 会根据输出文件名的扩展名自动选择合适的编码器。*

- **压缩 JPEG 图片 (控制质量):**
  ```bash
  ffmpeg -i input.jpg -q:v 4 output.jpg
  ```
  *说明：`-q:v` 用于控制视频流（此处指图片）的质量，值越小质量越高。对于 `mjpeg` 编码器，取值范围通常是 1-31，1 表示最高质量。*

- **将图片尺寸缩小一半:**
  ```bash
  ffmpeg -i input.png -vf "scale=iw/2:ih/2" output.png
  ```
  *说明：`-vf` 指定视频滤镜，`scale` 滤镜用于调整尺寸。`iw` 和 `ih` 分别代表输入图片的宽度和高度。*

- **创建 WebP 格式图片:**
  ```bash
  ffmpeg -i input.png -c:v libwebp -quality 80 output.webp
  ```
  *说明：`-c:v` 指定视频编码器为 `libwebp`，`-quality` 控制有损压缩的质量，范围 0-100。*

- **图像序列与 `image2` 命名模式:**
  ```bash
  # 从视频每秒截一帧输出为 PNG 序列
  ffmpeg -i input.mp4 -vf fps=1 "frames/out-%04d.png"
  # 将 PNG 序列以 10 fps 编码为 WebP（静态或动画按需使用）
  ffmpeg -framerate 10 -i "frames/out-%04d.png" -c:v libwebp out.webp
  ```

## 各格式压缩指南

本章节详细介绍针对不同图片格式的压缩和转换命令。

### JPEG

JPEG 是最常见的有损图片格式，适用于照片等色彩丰富的图像。FFmpeg 主要使用 `mjpeg` 编码器进行处理。

- **有损压缩 (控制质量):**
  ```bash
  ffmpeg -i input.jpg -q:v 5 output_quality_5.jpg
  ```
  *说明：`-q:v` 是控制质量的关键参数，范围通常为 1-31。数值越小，质量越高，文件体积越大。通常 2-10 之间是视觉质量和文件大小的良好平衡点。*

- **优化 Huffman 表 (减小体积):**
  ```bash
  ffmpeg -i input.jpg -huffman optimal output_optimal.jpg
  ```
  *说明：`-huffman optimal` 会计算并使用最优的 Huffman 表进行编码，可以在不牺牲质量的情况下，略微减小文件体积。*

### PNG

PNG 是无损压缩格式，支持透明通道，适合存储需要精确还原的图像，如图标、Logo、截图等。

- **无损压缩 (控制压缩级别):**
  ```bash
  ffmpeg -i input.png -compression_level 9 output_level_9.png
  ```
  *说明：PNG 的压缩是无损的。`-compression_level` 控制压缩算法的执行力度，范围是 0-9。级别越高，压缩时间越长，但可能获得更小的文件体积。默认值通常是 9。*

- **带 Alpha 通道 PNG 转 JPEG 的注意事项：**
  将带 alpha 通道的 PNG 转换为 JPEG 时，透明区域会被填充为黑色；如需自定义背景色（例如白色），通常需要结合更复杂的 `overlay` / `compose` 滤镜链，此处不展开。

### WebP

WebP 是 Google 开发的现代图片格式，同时支持有损和无损压缩，并提供优秀的压缩率。需要 FFmpeg 编译时包含 `libwebp`。

- **有损压缩 (推荐):**
  ```bash
  ffmpeg -i input.png -c:v libwebp -quality 80 output_q80.webp
  ```
  *说明：使用 `-c:v libwebp` 编码。`-quality` 是主要质量控制参数，范围 0-100。75-85 是一个很好的起点。*

- **无损压缩:**
  ```bash
  ffmpeg -i input.png -c:v libwebp -lossless 1 output_lossless.webp
  ```
  *说明：`-lossless 1` 开启无损模式。在此模式下，`-quality` 参数转为控制压缩速度与文件大小的平衡，100 表示最慢但体积最小。*

- **控制压缩速度与质量的平衡:**
  ```bash
  ffmpeg -i input.png -c:v libwebp -quality 75 -compression_level 6 output_q75_c6.webp
  ```
  *说明：`-compression_level` (0-6) 可以在有损和无损模式下使用，用于在编码速度和输出质量/体积之间做取舍。级别越高，编码时间越长，但压缩效果越好。*

- **像素格式提醒:** `libwebp` 在有损模式下通常使用 `yuv420p`，这可能会影响颜色精度。无损模式则支持 RGB。FFmpeg 会在需要时自动转换，但了解这一点有助于排查问题。

### AVIF

AVIF 是基于 AV1 视频编码的新一代图片格式，压缩效率极高。需要 FFmpeg 编译时包含 AV1 编码器（如 `libaom-av1` 或 `libsvtav1`）和 `avif` muxer。

- **有损压缩 (使用 libaom-av1):**
  ```bash
  ffmpeg -i input.png -c:v libaom-av1 -crf 30 -b:v 0 -frames:v 1 output.avif
  ```
  *说明：*
  * `-c:v libaom-av1`: 指定使用 libaom 作为 AV1 编码器。
  * `-crf 30`: 恒定速率因子（Constant Rate Factor），是主要的质量控制参数。数值越小，质量越高。推荐范围为 28-35。
  * `-b:v 0`: 设置目标比特率为 0，让编码器完全由 `-crf` 控制质量。
  * `-frames:v 1`: 因为我们是处理单张静态图片，所以设置只输出 1 帧。

- **有损压缩 (使用 libsvtav1):**
  ```bash
  ffmpeg -i input.png -c:v libsvtav1 -crf 35 -preset 8 output.avif
  ```
  *说明：`libsvtav1` 是另一个高效的 AV1 编码器。`-preset` 参数控制编码速度与效率的平衡，数值越大速度越快，但压缩效率可能略低。*

- **创建图片序列 (动画 AVIF):**
  如果你输入的是视频或图片序列，`avif` muxer 会自动创建动画 AVIF。
  ```bash
  ffmpeg -i input_video.mp4 -c:v libaom-av1 -crf 30 -b:v 0 output_animated.avif
  ```
  *说明：要控制动画循环次数，可以添加 `-loop` 参数。`-loop 0` 表示无限循环（默认）。`-loop -1` 表示不循环。*

### GIF

GIF 是一种古老的格式，色彩数有限且压缩效率低下。通常建议将其转换为现代的视频格式（如 MP4）或动画图片格式（如动画 WebP）。

- **优化 GIF:**
  FFmpeg 本身对 GIF 的优化有限，但可以通过滤镜生成更好的调色板来改善质量。
  ```bash
  ffmpeg -i input.gif -vf "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output_optimized.gif
  ```
  *说明：这个复杂的滤镜链首先分离输入流，一个用于生成优化的调色板，另一个用于应用这个调色板，从而在有限的 256 色内达到更好的效果。*

- **GIF 转 MP4 (推荐):**
  ```bash
  ffmpeg -i input.gif -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" output.mp4
  ```
  *说明：转换为 H.264 编码的 MP4 通常可以大幅减小文件体积，且画质更好。`-pix_fmt yuv420p` 确保了最大的播放器兼容性。*

- **GIF 转动画 WebP:**
  ```bash
  ffmpeg -i input.gif -c:v libwebp -loop 0 -lossless 0 -quality 80 output.webp
  ```
  *说明：将 GIF 转换为动画 WebP 也是一个很好的选择，兼顾了体积和质量。`-loop 0` 保持无限循环。*

## 尺寸、采样与批量处理

### 尺寸缩放 (Resizing)

使用 `-vf scale` 滤镜可以灵活地调整图片尺寸。

- **指定固定宽度，高度按比例缩放:**
  ```bash
  ffmpeg -i input.jpg -vf "scale=640:-1" output_w640.jpg
  ```
  *说明：将宽度设置为 640px，高度设置为 -1，FFmpeg 会自动计算并保持原始宽高比。*

- **指定固定高度，宽度按比例缩放:**
  ```bash
  ffmpeg -i input.jpg -vf "scale=-1:480" output_h480.jpg
  ```
  *说明：与上一个示例类似，但固定高度。*

- **确保尺寸是偶数 (兼容性):**
  某些视频编码器要求宽高为偶数。虽然这对大多数现代图片格式不是必须的，但在处理视频或兼容旧设备时很有用。
  ```bash
  ffmpeg -i input.jpg -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" output_even.jpg
  ```

### 批量处理

FFmpeg 本身不直接支持目录处理，但可以结合 Shell 脚本或 PowerShell 脚本轻松实现。

- **Linux / macOS (Bash):**
  将 `input_folder` 目录下的所有 `.png` 文件转换为 `.jpg` 格式，并存放到 `output_folder`。
  ```bash
  #!/bin/bash
  INPUT_DIR="input_folder"
  OUTPUT_DIR="output_folder"
  mkdir -p "$OUTPUT_DIR"
  for img in "$INPUT_DIR"/*.png; do
    filename=$(basename -- "$img")
    base="${filename%.*}"
    ffmpeg -i "$img" "$OUTPUT_DIR/$base.jpg"
  done
  ```

- **Windows (PowerShell):**
  功能同上，使用 PowerShell 语法。
  ```powershell
  $input_dir = "C:\path\to\input_folder"
  $output_dir = "C:\path\to\output_folder"
  if (-not (Test-Path $output_dir)) {
    New-Item -ItemType Directory -Path $output_dir
  }
  Get-ChildItem -Path $input_dir -Filter *.png | ForEach-Object {
    $baseName = $_.BaseName
    $outputFile = Join-Path $output_dir "$baseName.jpg"
    ffmpeg -i $_.FullName $outputFile
  }
  ```

### 元数据处理 (Metadata)

默认情况下，FFmpeg 会尝试保留输入文件中的元数据（如 EXIF 信息）。你可以明确控制这一行为。

- **丢弃所有元数据:**
  ```bash
  ffmpeg -i input.jpg -map_metadata -1 output_no_meta.jpg
  ```
  *说明：`-map_metadata -1` 会从输出文件中移除所有元数据流。*

- **复制全局元数据:**
  ```bash
  ffmpeg -i input.jpg -map_metadata 0 output_global_meta.jpg
  ```
  *说明：`-map_metadata 0` 会从输入文件 0 复制全局元数据到输出文件。对于单张图片，这通常等同于保留所有主要元数据，是比 `-map_metadata 0:s:v` 更稳妥的选择。*

## 常见问题 (FAQ)

### 1. 如何检查我的 FFmpeg 版本支持哪些编码器？

你可以使用以下命令列出所有可用的编码器。结合 `grep` (或 `findstr` on Windows) 可以快速查找特定的编码器。

- **列出所有编码器:**
  ```bash
  ffmpeg -encoders
  ```

- **检查是否支持 libwebp:**
  ```bash
  # Linux / macOS
  ffmpeg -encoders | grep libwebp
  
  # Windows
  ffmpeg -encoders | findstr libwebp
  ```
  *如果输出中包含 `libwebp` 的行，则表示支持。例如 `V..... libwebp              libwebp WebP image encoder (codec webp)`。*

- **检查是否支持 AV1 编码器 (如 libaom-av1):**
  ```bash
  # Linux / macOS
  ffmpeg -encoders | grep aom
  
  # Windows
  ffmpeg -encoders | findstr aom
  ```

### 2. 转换时遇到“Pixel format '...' not supported”错误怎么办？

这个错误意味着输入图片的像素格式不被目标编码器直接支持。例如，`libwebp` 在有损模式下主要支持 `yuv420p`。你可以通过 `-pix_fmt` 参数手动指定一个兼容的像素格式来解决。

```bash
# 尝试将输入转换为 yuv420p 像素格式
ffmpeg -i input.png -c:v libwebp -pix_fmt yuv420p output.webp
```

### 3. 如何查看 FFmpeg 支持的像素格式？

使用以下命令可以列出所有支持的像素格式。

```bash
ffmpeg -pix_fmts
```

## 参考链接

- **FFmpeg 官方文档 (总览):** [https://ffmpeg.org/ffmpeg.html](https://ffmpeg.org/ffmpeg.html)
- **FFmpeg Codecs 文档:** [https://ffmpeg.org/ffmpeg-codecs.html](https://ffmpeg.org/ffmpeg-codecs.html)
  - **libwebp 编码器选项:** [https://ffmpeg.org/ffmpeg-codecs.html#libwebp-1](https://ffmpeg.org/ffmpeg-codecs.html#libwebp-1)
  - **libaom-av1 编码器选项:** [https://ffmpeg.org/ffmpeg-codecs.html#libaom_002dav1](https://ffmpeg.org/ffmpeg-codecs.html#libaom_002dav1)
- **FFmpeg Formats 文档:** [https://ffmpeg.org/ffmpeg-formats.html](https://ffmpeg.org/ffmpeg-formats.html)
  - **image2 Muxer (用于图片序列):** [https://ffmpeg.org/ffmpeg-formats.html#image2-1](https://ffmpeg.org/ffmpeg-formats.html#image2-1)
  - **avif Muxer:** [https://ffmpeg.org/ffmpeg-formats.html#avif](https://ffmpeg.org/ffmpeg-formats.html#avif)
