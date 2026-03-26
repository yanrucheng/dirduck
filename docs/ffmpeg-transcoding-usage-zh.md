# FFmpeg 视频转码速查手册

本文档是一份面向工程师的 FFmpeg 视频转码速查指南，旨在覆盖 80% 的日常转码需求。它提供可直接复制粘贴的命令行示例，并附上关键参数的简明解释，帮助你快速、高效地完成视频处理任务。

## 1. 核心概念与基础参数

在深入具体命令之前，理解几个核心概念至关重要。

*   **容器 (Container) vs. 编码 (Codec)**：
    *   **容器**（如 MP4, MKV, MOV）是一种文件格式，它像一个箱子，把视频流、音频流和字幕等“打包”在一起。它决定了文件如何组织，但不直接决定画质。
    *   **编码**（如 H.264, HEVC, VP9, AV1）是压缩和解压视频/音频数据的方法。它直接关系到视频的压缩率和最终呈现的质量。

*   **流 (Stream)**：一个媒体文件通常包含多个流，例如一个视频流、一个或多个音频流、以及字幕流。FFmpeg 默认会自动选择各类流中“最好”的一个，但我们常常需要手动控制。

### 基础参数

FFmpeg 的参数分为全局参数和文件特有参数。文件特有参数的位置很重要，它作用于其后的第一个输入或输出文件。

*   `-i <input_file>`：指定输入文件。
*   `-hide_banner`：一个常用的全局参数，放在命令最开头，可以隐藏 FFmpeg 的编译信息和库版本等冗余打印，让日志更清爽。
*   `-c <codec>`, `-c:v <codec>`, `-c:a <codec>`：指定编码器。
    *   `-c` 是 `-codec` 的缩写，可同时指定音视频编码器。
    *   `-c:v` 单独指定视频编码器。
    *   `-c:a` 单独指定音频编码器。
    *   特殊值 `copy` 表示直接复制流，不做重新编码，即“流复制”或“remux”，速度极快且无质量损失。
*   `-map <stream_specifier>`：手动选择要处理和输出的流。这是精确控制多路流（如多音轨、多字幕）的关键。
    *   `-map 0:v:0`：选择第一个输入文件（`0`）的第一个视频流（`v:0`）。
    *   `-map 0:a`：选择第一个输入文件的所有音频流。
    *   `-map -0:s`：排除第一个输入文件的所有字幕流。
*   `-threads <number>`：设置用于转码的线程数。通常设置为 `0` 允许 FFmpeg 自动选择最佳线程数。对于某些编码器，这能显著提升速度。

**基本命令结构：**

```bash
ffmpeg -hide_banner -i input.mp4 [输出选项] output.mkv
```
---

接下来，我们将深入探讨各种主流视频编码器的具体用法。

## 2. 主流视频编码器实践

选择合适的编码器和参数是在质量、文件大小和编码速度之间取得平衡的关键。

### H.264 (libx264) - 兼容性之王

`libx264` 是高质量的开源 H.264 编码器，具有无与伦比的兼容性，几乎所有设备都支持。

*   **CRF (Constant Rate Factor) 模式**：**推荐！**
    这是最常用也是最推荐的码率控制模式。它在整个视频中追求恒定的“感知质量”，而非恒定的码率。CRF 值越低，质量越高，文件越大。
    *   **推荐范围**：`18` (视觉无损) ~ `28` (可接受的压缩)。通常 `23` 是一个很好的默认值。

    ```bash
    # 使用 CRF 23 进行高质量转码
    ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a copy output.mp4
    ```
    *   **-preset <speed>**：决定编码速度和压缩效率的平衡。可选值有 `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium` (默认), `slow`, `slower`, `veryslow`。`preset` 越慢，压缩率越高（文件更小），但耗时更长。`medium` 到 `fast` 是常见选择。

*   **Profile & Level**：控制编码特性的集合，影响兼容性。
    *   **-profile:v <profile>**：
        *   `baseline`：兼容性最好，适用于老旧设备或某些视频会议场景。
        *   `main`：标准质量。
        *   `high`：主流选择，提供最佳压缩效率。
    *   **-level <level>**：限制码率和分辨率等参数的上限。通常无需手动设置，编码器会根据分辨率和帧率自动选择。

    ```bash
    # 针对移动端优化，保证兼容性
    ffmpeg -i input.mp4 -c:v libx264 -profile:v main -crf 24 -preset fast output.mp4
    ```

### H.265 / HEVC (libx265) - 高效压缩

HEVC (High Efficiency Video Coding) 能以 H.264 约一半的码率实现同等画质，但编码耗时更长，且部分老旧设备不支持硬解。

*   **CRF 模式 (libx265)**：与 libx264 类似，但 CRF 值的标度不同。
    *   **推荐范围**：`22` ~ `32`。通常 `28` 是一个不错的起点，大致相当于 libx264 的 `23`。

    ```bash
    # 使用 HEVC 进行高效压缩，preset 同样适用
    ffmpeg -i input.mp4 -c:v libx265 -crf 28 -preset medium -c:a copy output.mp4
    ```
    *   **-tag:v hvc1**：添加这个参数可以提高在 Apple 设备上的兼容性。

### VP9 (libvpx-vp9) - 开放标准

VP9 是由 Google 开发的开放、免版税的编码格式，在 Web 视频（如 YouTube）中广泛使用。其压缩效率与 HEVC 相当。

*   **CRF 模式 (libvpx-vp9)**：
    *   **推荐范围**：`30` ~ `40`。`33` 是一个不错的起点。
    *   **-b:v 0**：使用 CRF 模式时，必须将 `-b:v` (视频码率) 设置为 `0`。

    ```bash
    # 转码为 VP9 格式，适用于 Web 播放
    ffmpeg -i input.mp4 -c:v libvpx-vp9 -crf 33 -b:v 0 -c:a libopus output.webm
    ```
    *   **音频编码**：`.webm` 容器通常搭配 `libopus` 音频编码。

### AV1 (libaom-av1 / libsvtav1) - 下一代标准

AV1 是最新的开放编码标准，压缩效率比 HEVC/VP9 更高，但编码过程极其缓慢，目前主要用于特定场景的点播分发。

*   **libsvtav1 (SVT-AV1)**：由 Intel 和 Netflix 联合开发，是目前速度最快的 AV1 编码器，推荐使用。
*   **CRF 模式 (libsvtav1)**：
    *   **推荐范围**：`30` ~ `50`。可以从 `35` 开始尝试。
    *   **-preset <number>**：SVT-AV1 的 `preset` 是数字 `0` (最高质量) 到 `12` (最快速度)。通常 `8` 是一个不错的平衡点。

    ```bash
    # 使用 SVT-AV1 进行编码，注意 preset 是数字
    ffmpeg -i input.mp4 -c:v libsvtav1 -crf 35 -preset 8 -g 240 -c:a libopus output.mkv
    ```

### 通用视频参数

以下参数对大多数编码器都有效：

*   `-g <number>`：设置关键帧 (GOP, Group of Pictures) 间隔。即每隔多少帧强制插入一个 I 帧。通常设置为帧率的 2-10 倍，例如对于 24fps 的视频，可以设置为 `48` 或 `240`。合理的 GOP 间隔有助于改善拖动（seek）性能和压缩效率。
*   `-movflags +faststart`：**强烈推荐用于 MP4！** 此参数会将 moov atom（包含索引信息）从文件末尾移动到开头。这使得视频无需完全下载即可开始播放，对于网络流媒体至关重要。

> **注意**：CRF 值只是一个参考，最佳取值取决于源视频的质量、内容复杂度以及你对输出质量的要求。建议用一小段视频进行测试，找到最适合你场景的 CRF 值。

## 3. 硬件加速：释放 GPU 的力量

硬件加速（Hardware Acceleration）利用 GPU 或专用芯片来执行计算密集的编码/解码任务，可以数十倍地提升转码速度，但代价通常是轻微的质量损失和更大的文件体积（相比于同等质量的软件编码）。

### 工作流程：数据从 CPU 到 GPU 再返回

硬件加速的核心在于减少 CPU 和 GPU 之间的数据拷贝。理想的流程是：
1.  **硬件解码**：数据从磁盘读入内存后，直接送入 GPU 进行解码。
2.  **GPU 内处理**：视频帧在 GPU 显存中进行滤镜处理（如缩放）。
3.  **硬件编码**：处理后的帧直接在 GPU 上进行编码。
4.  **数据拷回**：编码后的数据包从 GPU 拷回 CPU 内存，然后写入文件。

### 常见硬件加速技术与 FFmpeg 编码器

| 厂商/技术 | 支持的编码器 (示例)                  | 特点                                       |
| :-------- | :----------------------------------- | :----------------------------------------- |
| **NVIDIA**| `h264_nvenc`, `hevc_nvenc`           | 消费级和专业级显卡均支持，性能强大，配置灵活。 |
| **Intel** | `h264_qsv`, `hevc_qsv`, `vp9_qsv`  | 集成在 Intel CPU 中（核显），通用性好，无需独立显卡。 |
| **AMD/Generic** | `h264_vaapi`, `hevc_vaapi`         | VAAPI 是 Linux 下的通用视频加速 API，AMD 和 Intel 显卡均支持。 |

### 基本用法示例

#### NVIDIA NVENC

使用 NVENC 需要先通过 `-hwaccel cuda` (或 `cuvid`，较旧) 让 FFmpeg 启用 CUDA 加速。

```bash
# 使用 NVENC 进行 H.264 硬件编码
ffmpeg -hwaccel cuda -i input.mp4 -c:v h264_nvenc -preset p5 -cq 24 -c:a copy output.mp4
```

*   **-hwaccel cuda**：指定使用 CUDA 进行硬件加速解码。
*   **-c:v h264_nvenc**：选择 NVENC H.264 编码器。
*   **-preset <p1-p7>**：NVENC 的 preset 分为 `p1` (最快) 到 `p7` (最慢，最高质量)。`p5` 是一个很好的平衡点。
*   **-cq <number>**：恒定质量（Constant Quality）模式，类似 CRF。对于 NVENC，推荐范围 `20` ~ `28`。

#### Intel QSV (Quick Sync Video)

QSV 通常需要指定一个 QSV 设备，并处理像素格式的上传。

```bash
# 使用 QSV 进行 HEVC 硬件编码，并进行缩放
ffmpeg -hwaccel qsv -i input.mp4 -vf "scale_qsv=w=1280:h=720" -c:v hevc_qsv -preset medium -global_quality 25 -c:a copy output.mp4
```

*   **-hwaccel qsv**：启用 QSV 加速解码。
*   **-vf "scale_qsv=..."**：使用 QSV 特定的滤镜 `scale_qsv` 在 GPU 上进行缩放，避免数据拷回 CPU。
*   **-c:v hevc_qsv**：选择 QSV HEVC 编码器。
*   **-global_quality <number>**：QSV 的质量参数，类似 CRF，范围 `1` ~ `51`。`25` 是一个不错的起点。

#### Linux VAAPI

VAAPI 的设置相对复杂，需要正确配置 DRI (Direct Rendering Infrastructure)。

```bash
# 使用 VAAPI 进行 H.264 硬件编码
ffmpeg -hwaccel vaapi -hwaccel_output_format vaapi -i input.mp4 -vf 'format=nv12|vaapi,hwupload' -c:v h264_vaapi -qp 24 -c:a copy output.mp4
```

*   **-hwaccel_output_format vaapi**：确保解码器输出的帧格式是 VAAPI 兼容的。
*   **-vf 'format=nv12|vaapi,hwupload'**：这是一个关键步骤。`hwupload` 将 CPU 内存中的帧上传到 GPU 显存。`format=nv12|vaapi` 确保像素格式正确。
*   **-qp <number>**：量化参数（Quantization Parameter），也是一种质量控制方式，数值越小质量越高。

### 像素格式与 `hwupload`

*   **像素格式 (Pixel Format)**：CPU 处理的视频帧（如 `yuv420p`）和 GPU 处理的视频帧（如 `nv12`, `p010le`）格式不同。
*   **-pix_fmt <format>**：当你不确定或遇到颜色错误时，可以手动指定输出像素格式。`yuv420p` 是兼容性最好的选择。
*   **`hwupload` 与 `hwdownload`**：
    *   `hwupload` 滤镜：将数据从 CPU 上传到 GPU。
    *   `hwdownload` 滤镜：将数据从 GPU 下载回 CPU。
    *   如果你需要在 CPU 上执行某个滤镜（例如，一个只有 CPU 实现的滤镜），就必须先 `hwdownload`，处理完后再 `hwupload`，这会降低性能。

> **踩坑点**：
> *   硬件编码的质量通常不如软件编码（如 libx264）精细。如果追求极致画质，请使用软件编码。
> *   驱动程序是关键！确保你的 NVIDIA/Intel 驱动已正确安装并是最新版本。
> *   `ffmpeg -hwaccels` 可以列出当前构建支持的所有硬件加速方法。
> *   `ffmpeg -encoders | grep nvenc` (或 `qsv`, `vaapi`) 可以查看支持的具体硬编码器。
> *   遇到 "Impossible to convert between a software format and a hardware format" 之类的错误时，通常是缺少 `hwupload` 或者 `format` 指定不正确。

## 4. 画面与时序调整

转码过程中经常需要对画面尺寸、帧率等进行调整。

### 分辨率缩放 (`scale`)

`scale` 滤镜是最常用的视频滤镜之一。

```bash
# 将视频缩放至 1280x720
ffmpeg -i input.mp4 -vf "scale=1280:720" -c:v libx264 -crf 23 -c:a copy output.mp4
```

*   **保持宽高比**：通常我们希望在缩放时保持原始视频的宽高比。
    *   `scale=1280:-1`：将宽度设为 1280px，高度按比例自动计算。
    *   `scale=-1:720`：将高度设为 720px，宽度按比例自动计算。
*   **避免不必要的拉伸**：为防止拉伸，可以结合 `force_original_aspect_ratio`。

    ```bash
    # 在 1920x1080 的黑边背景上，保持原始比例缩放视频
    ffmpeg -i input.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" output.mp4
    ```
    *   `force_original_aspect_ratio=decrease`：确保视频被缩小以适应指定尺寸，而不会被放大。
    *   `pad=...`：在缩放后的视频周围添加黑边，使其最终尺寸为 1920x1080。

### 帧率转换 (`-r` 或 `fps` 滤镜)

*   **-r <fps>**：作为输出选项时，它会通过丢弃或复制帧的方式强制改变输出视频的帧率，这可能会导致画面卡顿或不流畅。**不推荐用于改变已有视频的帧率。**
*   **`fps` 滤镜**：**推荐！** 它通过混合相邻帧来创建平滑的帧率过渡。

```bash
# 将视频帧率平滑转换为 30fps
ffmpeg -i input.mp4 -vf "fps=30" -c:v libx264 -crf 23 -c:a copy output.mp4
```

### 像素格式 (`pix_fmt`) 与色彩空间

*   **-pix_fmt <format>**：指定输出的像素格式。
    *   `yuv420p`：**兼容性之王**。这是网络视频和大多数设备最广泛支持的格式。如果遇到播放器颜色异常（例如，颜色偏绿或紫），首先检查并确保像素格式为 `yuv420p`。
*   **色彩空间与 HDR**：处理 HDR (高动态范围) 视频时，需要确保色彩空间信息（如 `bt2020`）、转移特性（如 `smpte2084`）和色彩原色（如 `bt2020`）在转码过程中被正确保留或转换。
    *   简单的 SDR 转码通常无需关心此项，FFmpeg 会自动处理。
    *   对于 HDR -> SDR 的转换（色调映射），需要使用 `zscale` 或 `tonemap` 等复杂滤镜。

    ```bash
    # 确保输出为 yuv420p，以获得最大兼容性
    ffmpeg -i input.mov -c:v libx264 -pix_fmt yuv420p -crf 22 output.mp4
    ```

## 5. 音频处理

音频质量同样重要。以下是常见的音频编码和处理选项。

### 常用音频编码器

| 编码器   | 特点                                      | 常用容器 |
| :------- | :---------------------------------------- | :------- |
| **aac**  | 兼容性极好，是 MP4 文件的标准音频编码。     | `.mp4`   |
| **libopus**| 开放、免版税，在较低码率下表现优于 AAC，常用于 WebM。 | `.webm`  |
| **ac3**  | 主要用于影碟和广播，支持多声道。          | `.mkv`   |
| **copy** | 直接复制音频流，无质量损失。              | 任何     |

### 常用参数

*   **-b:a <bitrate>**：设置音频码率。
    *   AAC: `128k` (不错) 到 `192k` (高质量) 是立体声的常用范围。
    *   Opus: `96k` 到 `128k` 即可提供很好的立体声效果。
*   **-ar <rate>**：设置音频采样率（单位 Hz）。`44100` 或 `48000` 是标准值。通常无需更改。
*   **-ac <channels>**：设置声道数。`2` 表示立体声，`1` 表示单声道。

```bash
# 将音频转为 192kbps 的 AAC 立体声
ffmpeg -i input.mkv -c:v copy -c:a aac -b:a 192k -ac 2 output.mp4
```

### 响度标准化 (`loudnorm`)

不同来源的视频音量大小不一，`loudnorm` 滤镜可以将其标准化到一个统一的响度水平，提升观看体验。这是一个两阶段的过程。

**第一阶段：分析**

```bash
# 分析音频响度，不实际输出文件
ffmpeg -i input.mp4 -af loudnorm=I=-16:LRA=11:tp=-1.5:print_format=json -f null -
```
*   `I=-16`：目标综合响度为 -16 LUFS (一个常见的流媒体标准)。
*   `LRA=11`, `tp=-1.5`：响度范围和真峰值限制。
*   `print_format=json`：将分析结果以 JSON 格式打印到控制台。

**第二阶段：应用**

从第一阶段的输出中找到 `measured` 值，并将其填入第二阶段的命令中。

```bash
# 假设从第一阶段得到 "input_i": "-23.5", "input_tp": "0.5", ...
ffmpeg -i input.mp4 -af "loudnorm=I=-16:LRA=11:tp=-1.5:measured_I=-23.5:measured_tp=0.5:..." -c:v copy -ar 48k output.mp4
```

> **提示**：响度标准化是一个复杂话题，上述参数是 EBU R128 建议的一个起点。对于简单应用，仅指定 `I` 值通常就足够了。

## 6. 复用与切片

### 流复制 (`-c copy`)：只换容器，不编码

当你只是想改变文件的容器格式（例如，从 `.mkv` 转到 `.mp4`），或者剪切视频而不需要重新编码时，`copy` 是最理想的选择。

*   **优点**：
    *   **速度极快**：因为它只复制数据，不进行任何计算密集的编解码。
    *   **无质量损失**：原始的音视频数据被原封不动地保留。
*   **适用场景**：
    *   MKV 转 MP4，前提是内部编码兼容（例如，视频是 H.264，音频是 AAC）。
    *   从长视频中快速剪辑一小段。
    *   添加或移除字幕、音轨。

```bash
# 将 MKV 容器转换为 MP4 容器，假设内部编码兼容
ffmpeg -i input.mkv -c copy -movflags +faststart output.mp4
```
> **限制**：并非所有编码格式都能被所有容器支持。例如，FLV 容器就不支持 HEVC 编码。如果遇到 "Could not find tag for codec ... in stream" 错误，就意味着目标容器不支持源编码，此时必须进行重新编码。

### HTTP 流媒体切片：HLS & DASH

HLS (HTTP Live Streaming) 和 DASH (Dynamic Adaptive Streaming over HTTP) 是现代流媒体的基石。它们将视频文件切分成一系列小片段（通常是 `.ts` 或 `.m4s` 文件）和一个播放列表（`.m3u8` 或 `.mpd`），客户端可以根据网络状况动态切换不同码率的片段。

#### HLS 快速示例

```bash
# 生成 HLS 切片，每 4 秒一个片段
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k \
-f hls -hls_time 4 -hls_playlist_type vod -hls_segment_filename "segment%03d.ts" playlist.m3u8
```

*   **-f hls**：指定输出格式为 HLS。
*   **-hls_time <seconds>**：设置每个切片的时长。
*   **-hls_playlist_type vod**：指定为点播（Video on Demand）播放列表。如果是直播，则为 `event`。
*   **-hls_segment_filename "segment%03d.ts"**：定义切片文件的命名规则，`%03d` 会被替换为 `001`, `002`...

#### DASH 快速示例

DASH 的生成通常更复杂，因为它鼓励将音视频分离。

```bash
# 生成 DASH 清单和相应的媒体片段 (视频和音频分离)
ffmpeg -i input.mp4 -map 0:v:0 -c:v libx264 -crf 23 -an -f dash video_init.mp4 \
-map 0:a:0 -c:a aac -b:a 128k -vn -f dash audio_init.mp4 \
-f dash manifest.mpd
```

*   这个命令会为视频和音频分别创建初始化片段和数据片段，并生成一个 `manifest.mpd` 文件。实际生产中，通常会为不同码率创建多组流。

## 7. 进阶工作流

### 两遍编码 (2-Pass)：精确码率控制

当你需要严格控制输出文件的大小（例如，为特定带宽的流媒体准备）时，两遍编码是最佳选择。它牺牲时间换取对码率的精确控制和更高的编码效率。

**第一遍 (Pass 1)：分析**
此遍会分析视频内容，并将统计信息写入一个日志文件 (`.log`)，但不生成有效的视频文件。

```bash
# -an 禁用音频, -f null 不输出文件
ffmpeg -y -i input.mp4 -c:v libx264 -b:v 5M -preset medium -pass 1 -an -f null /dev/null
```

**第二遍 (Pass 2)：编码**
此遍利用第一遍生成的日志文件，以指定的码率进行高质量编码。

```bash
ffmpeg -i input.mp4 -c:v libx264 -b:v 5M -preset medium -pass 2 -c:a aac -b:a 192k output.mp4
```
*   `-b:v 5M`：指定目标视频码率为 5 Mbps。
*   `-pass 1` / `-pass 2`：分别指定第一遍和第二遍。

### 裁剪 (`-ss`, `-to`, `-t`)：精确与快速

*   **快速但不精确 (输入前 `-ss`)**：
    将 `-ss` 放在 `-i` 之前，FFmpeg 会利用 I 帧进行快速跳转（seek），速度非常快，但开始时间可能不完全精确。

    ```bash
    # 从第 10 秒开始，剪辑 5 秒钟的视频 (快速)
    ffmpeg -ss 00:00:10 -i input.mp4 -t 5 -c copy output.mp4
    ```

*   **精确但较慢 (输入后 `-ss`)**：
    将 `-ss` 放在 `-i` 之后，FFmpeg 会先解码所有帧，然后再从精确的时间点开始处理，非常精确，但如果视频很长，会慢很多。

    ```bash
    # 从第 10.5 秒开始，剪辑到第 15 秒 (精确)
    ffmpeg -i input.mp4 -ss 00:00:10.5 -to 00:00:15 -c:v libx264 -c:a aac output.mp4
    ```
    *   `-t <duration>`：指定剪辑的时长。
    *   `-to <time>`：指定剪辑的结束时间点。`-t` 和 `-to` 通常只用一个。

### 字幕处理

*   **内嵌字幕 (硬字幕)**：将字幕“烧录”到视频画面中，成为视频的一部分。
    ```bash
    # 将 subtitle.srt 字幕文件烧录到视频中
    ffmpeg -i input.mp4 -vf "subtitles=subtitle.srt" output.mp4
    ```

*   **复制字幕 (软字幕)**：将字幕流从一个容器复制到另一个容器，用户可以在播放器中开关。
    ```bash
    # 假设 input.mkv 的第三个流是字幕流 (0:s:0)
    ffmpeg -i input.mkv -map 0:v -map 0:a -map 0:s:0 -c copy output.mkv
    ```

### 视频拼接 (`concat`)

拼接多个具有**相同编码、分辨率、帧率**的视频。

1.  创建一个 `mylist.txt` 文件，内容如下：
    ```
    file 'part1.mp4'
    file 'part2.mp4'
    file 'part3.mp4'
    ```
2.  执行拼接命令：
    ```bash
    # 使用 concat demuxer 进行拼接
    ffmpeg -f concat -safe 0 -i mylist.txt -c copy output_combined.mp4
    ```
    *   `-f concat`：使用 concat demuxer。
    *   `-safe 0`：允许使用绝对路径（出于安全考虑，默认禁用）。
    *   如果视频参数不一致，需要先将它们分别转码为统一格式，再进行拼接。

## 8. 排错与兼容性

转码过程中总会遇到各种问题，以下是一些常见的排错技巧和为了保证兼容性的最佳实践。

### 使用 `ffprobe` 定位问题

`ffprobe` 是一个与 `ffmpeg` 配套的强大分析工具，它可以详细展示媒体文件的各种信息，是排错的第一步。

```bash
# 显示文件的所有流信息
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

*   **-v quiet**：隐藏 ffprobe 的 banner 和日志，只输出结果。
*   **-print_format json**：以易于阅读和机器解析的 JSON 格式输出。
*   **-show_format**：显示容器格式信息（时长、码率等）。
*   **-show_streams**：显示所有流的详细信息（编码、分辨率、帧率、像素格式等）。

通过检查 `ffprobe` 的输出，你可以快速确认：
*   视频和音频的**编码格式 (codec_name)** 是否符合预期？
*   **像素格式 (pix_fmt)** 是否是兼容性好的 `yuv420p`？
*   **分辨率 (width, height)** 和 **帧率 (avg_frame_rate)** 是多少？
*   是否存在多个视频或音频流？

### 移动端/网页播放兼容性

为了让视频在最广泛的设备上（尤其是移动端浏览器）顺利播放，请遵循以下“安全”实践：

1.  **编码**: H.264 (libx264) 是最安全的选择。
2.  **Profile**: 使用 `baseline` 或 `main` profile。`high` profile 虽然压缩率更高，但在非常老旧的设备上可能不支持。
    ```bash
    -profile:v main
    ```
3.  **像素格式**: 必须是 `yuv420p`。
    ```bash
    -pix_fmt yuv420p
    ```
4.  **音频**: AAC 是最佳选择。
5.  **MOOV Atom**: 对于 MP4 容器，务必使用 `-movflags +faststart`，否则视频需要完全下载后才能播放。

**一个兼容性优先的转码命令示例：**
```bash
ffmpeg -i input.mov -c:v libx264 -profile:v main -pix_fmt yuv420p -crf 24 -preset fast \
-c:a aac -b:a 128k -movflags +faststart -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" output.mp4
```
*   **-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"**：这是一个保护性措施，确保视频的宽和高都是偶数。某些老的 H.264 解码器处理奇数分辨率时会有问题。

### 常见“坑”与注意事项

*   **时间戳问题 (VFR vs. CFR)**：
    *   **VFR (Variable Frame Rate)**：可变帧率，常见于屏幕录制、手机拍摄的视频。如果处理不当，可能导致音画不同步。
    *   **CFR (Constant Frame Rate)**：恒定帧率。
    *   当你怀疑是 VFR 导致的问题时，可以在转码时强制设为 CFR，例如使用 `fps` 滤镜：`-vf "fps=30"`。

*   **封装差异**:
    *   从 MKV 转到 MP4 时，某些 MKV 特有的高级功能（如章节、复杂的字幕格式）可能会丢失。
    *   `avi` 是一个非常古老的容器，避免使用它来封装现代编码（如 HEVC, AV1）。

*   **"Error while opening decoder for input stream..."**:
    *   这个错误通常意味着你的 FFmpeg 构建版本不支持该输入流的编码格式。你可能需要一个带有更多解码器库的 FFmpeg 版本（例如，包含 `libaacs` 等的“full”版本）。
    *   也可能是文件本身已损坏。

*   **"Past duration ... too large"**:
    *   这个警告常见于流复制 (`-c copy`) 模式，特别是处理 `.ts` 文件时。它通常是由于源文件的时间戳不连续造成的。
    *   在很多情况下可以安全地忽略，但如果导致了问题，可以尝试对音视频流进行重新编码而非复制，这会生成新的、连续的时间戳。

---

**最后，请记住**：FFmpeg 的功能远不止于此。当遇到特定问题时，查阅官方文档或使用 `ffmpeg -h full`、`ffmpeg -h encoder=<encoder_name>`、`ffmpeg -h filter=<filter_name>` 来获取最详细的帮助。希望这份速查手册能为你提供一个坚实的起点。
