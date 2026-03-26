# FFmpeg 资源分配与硬件加速速查指南

FFmpeg 作为强大的多媒体处理工具，其性能表现很大程度上取决于资源分配策略。本指南聚焦于如何有效控制 FFmpeg 的 CPU/GPU 使用与线程并发，覆盖主流硬件加速框架，旨在为工程师与运维人员提供一份面向实操的速查手册。

## 1. 通用资源分配选项（CPU 与软件处理）

这些选项是独立于任何特定硬件的通用参数，主要用于控制 CPU 核心使用、线程行为和处理队列，是软件编解码和滤镜处理的基础。[[87]](https://ffmpeg.org/ffmpeg.html?utm_source=chatgpt.com)

| 选项 | 用途 | 适用阶段 | 注意事项与示例 |
| :--- | :--- | :--- | :--- |
| `-threads <整数>` | 设置用于编解码的线程数。 | 编码、解码 |  `0` 或 `auto` 通常表示自动选择（推荐）。某些编解码器（如 `libx264`）有自己的内建多线程，此选项可能不生效或表现不同。::cite[4787] <br> **示例**：`-threads 8` |
| `-filter_threads <整数>` | 设置处理单个简单滤镜链（`-vf`/`-af`）的线程数。 | 滤镜 | 对单个滤镜链（filterchain）生效。如果你的滤镜链本身是瓶颈，增加此值可能提升性能。默认为 CPU 核心数。::cite[1968] <br> **示例**：`-filter_threads 4` |
| `-filter_complex_threads <整数>` | 设置处理复杂滤镜图（`-filter_complex`）的线程数。 | 复杂滤镜 | 类似于 `-filter_threads`，但专门用于 `-filter_complex` 定义的滤镜图。当图中有多个并行处理的分支时，此选项尤其重要。默认为 CPU 核心数。::cite[3363] <br> **示例**：`-filter_complex_threads 8` |
| `-thread_queue_size <整数>` | 设置每个线程（输入或输出）的数据包队列大小。 | 输入、输出 | 在处理高码率直播流或多输入时，增大此值可防止因队列溢出而丢包。默认值较小（8），对于 UDP 等协议建议调高。::cite[3385] <br> **示例**：`-thread_queue_size 512` |
| `-cpuflags <标志>` | 手动设置或清除 CPU 优化标志。 | 全局 | **仅供测试和调试！** 用于强制启用或禁用特定的 CPU 指令集（如 `sse4.2`, `avx2`）。错误使用可能导致崩溃或性能下降。::cite[1183] <br> **示例**：`-cpuflags -avx2` (禁用 AVX2) |
| `-benchmark` | 在任务结束时输出性能基准测试信息。 | 全局 | 显示实际耗时（real time）、用户态耗时（user time）、系统态耗身（sys time）以及峰值内存使用量，是评估性能和优化的关键工具。::cite[2972] <br> **示例**：`ffmpeg -i in.mp4 ... out.mp4 -benchmark` |
| `-benchmark_all` | 在处理过程中持续输出各阶段的性能信息。 | 全局 | 比 `-benchmark` 更为详细，会分别打印解码、编码、滤镜等各个环节的耗时，便于定位具体瓶颈。::cite[2978] |

**核心理念**：

*   **解码/编码线程**：`-threads` 主要影响编解码器内部的并行处理能力。对于现代编解码器（如 x264, x265, vp9），将此值设为 `0` (自动) 通常是最佳实践。
*   **滤镜线程**：当视频/音频滤镜（如 `scale`, `overlay`, `atempo`）成为瓶颈时，通过 `-filter_threads` 或 `-filter_complex_threads` 分配更多 CPU 核心可以显著提速。
*   **队列管理**：`-thread_queue_size` 是处理实时或高速输入流时的“保险丝”，避免因处理速度跟不上输入速度而丢失数据。

---

## 2. 硬件加速总览与通用选项

硬件加速利用 GPU (或其他专用硬件，如 Intel QSV) 来执行计算密集型的解码、编码或滤镜操作，极大地降低 CPU 负载并提升处理速度。

FFmpeg 通过一系列通用选项来启用和配置硬件加速。

| 选项 | 用途 | 适用阶段 | 注意事项与示例 |
| :--- | :--- | :--- | :--- |
| `-hwaccel <api>` | 在输入端启用指定的硬件加速 API 进行解码。 | 输入（解码） | 这是启用硬件解码的主要开关。`auto` 会尝试自动选择可用的方法。常见值包括 `cuda`, `qsv`, `vaapi`, `dxva2`, `d3d11va`, `videotoolbox`。::cite[2619] <br> **示例**：`-hwaccel cuda` |
| `-hwaccel_output_format <api>` | 指定硬件解码后的帧数据格式。 | 输入（解码） | **关键选项**。为了保持数据在 GPU 内存中，应将其设置为硬件加速 API 对应的格式（如 `cuda`, `qsv`, `vaapi`）。这避免了将解码后的帧下载到系统内存（CPU），是实现“零拷贝”转码的前提。[[63]](https://gist.github.com/Brainiarc7/95c9338a737aa36d9bb2931bed379219?permalink_comment_id=3073215) <br> **示例**：`-hwaccel_output_format cuda` |
| `-hwaccel_device <索引或路径>` | 选择要使用的特定 GPU 设备。 | 输入（解码） | 当系统存在多个 GPU 时，用此选项指定使用哪一个。设备标识符的格式因 API 而异（如 `0`, `1` for CUDA, `/dev/dri/renderD128` for VAAPI）。::cite[2663] <br> **示例**：`-hwaccel_device 1` |
| `-init_hw_device <type>[=<name>@<source>]` | 初始化一个硬件设备以供滤镜使用。 | 全局/滤镜 | 用于创建和命名硬件设备上下文，尤其是在需要软件解码但使用硬件滤镜（如 `scale_cuda`）的场景。::cite[2385] <br> **示例**：`-init_hw_device cuda=gpu1:1` |
| `-filter_hw_device <name>` | 将已初始化的硬件设备传递给滤镜。 | 滤镜 | 配合 `-init_hw_device` 使用，告诉 `hwupload` 或硬件滤镜使用哪个 GPU 设备。::cite[2608] |

**核心理念：保持帧在 GPU 内存中（零拷贝）**

硬件加速的性能优势最大化，关键在于避免不必要的数据在 GPU 显存与系统内存之间来回拷贝。

1.  **解码到 GPU**：使用 `-hwaccel <api>` 和 `-hwaccel_output_format <api>`，确保解码后的原始视频帧直接存在于 GPU 显存中。
2.  **GPU 内处理**：如果需要对视频进行滤镜操作（如缩放、叠加），应优先使用该硬件加速框架对应的滤镜，例如：
    *   NVIDIA: `scale_npp`, `scale_cuda`
    *   Intel: `scale_qsv`, `vpp_qsv`
    *   Linux (VAAPI): `scale_vaapi`
    *   Vulkan: `scale_vulkan`
3.  **从 GPU 编码**：直接将处理完的 GPU 帧送入硬件编码器（如 `h264_nvenc`, `hevc_qsv`）。
4.  **上传/下载**：
    *   `hwupload` / `hwupload_cuda` 滤镜：当输入是软件解码（CPU 处理）的普通帧时，此滤镜可将其上传到 GPU 显存，以便后续使用硬件滤镜或硬件编码。
    *   `hwdownload` 滤镜：当 GPU 处理完的帧需要被一个仅支持 CPU 的滤镜处理，或者需要输出为原始视频（YUV）时，此滤镜负责将其从 GPU 显存下载回系统内存。频繁的上传下载会严重影响性能。

---

## 3. 各硬件/平台加速框架详解

### 3.1 NVIDIA (NVDEC/NVENC)

NVIDIA 的硬件编解码器分别称为 NVDEC (解码) 和 NVENC (编码)，通过 CUDA API 与 FFmpeg 集成。[[4]](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/ffmpeg-with-nvidia-gpu/index.html)

-   **通用解码选项**: `-hwaccel cuda`
-   **解码器**: `h264_cuvid`, `hevc_cuvid`, `av1_cuvid` 等 (老版本) 或直接使用 `-hwaccel cuda` (推荐)。
-   **编码器**: `h264_nvenc`, `hevc_nvenc`, `av1_nvenc`。
-   **GPU 滤镜**: `scale_npp`, `scale_cuda`, `hwdownload`, `hwupload_cuda`。

**关键选项与用法**

| 选项 (用于 `*_nvenc` 编码器) | 用途 | 注意事项与示例 |
| :--- | :--- | :--- |
| `-preset <preset>` | 控制编码速度与质量的权衡。 | 从 `p1` (最快) 到 `p7` (最慢，质量最好)。`p5` 是一个很好的平衡点。::cite[443] <br> **示例**：`-preset p5` |
| `-tune <tune>` | 针对特定场景优化。 | `hq` (高质量), `ll` (低延迟), `ull` (超低延迟)。::cite[464] <br> **示例**：`-tune hq` |
| `-cq <值>` 或 `-rc constqp` | 恒定质量模式。类似于软件编码的 `-crf`。 | 数值越低，质量越高。通常范围在 0-51。是 VBR 的一种形式。 <br> **示例**：`-cq 23` |
| `-b:v <比特率>` | 目标比特率（VBR 或 CBR）。 |  <br> **示例**：`-b:v 5M` |
| `-gpu <索引>` | **(已废弃)** 选择要使用的 GPU。 | 老版本 FFmpeg 使用此方式。现在推荐使用 `-hwaccel_device` 或 `-init_hw_device`。 <br> **示例**：`-gpu 1` |
| `-init_hw_device cuda=<name>:<idx>` | **(推荐)** 初始化特定 GPU 设备。 |  `idx` 是 `nvidia-smi` 命令显示的 GPU 索引。 <br> **示例**: `-init_hw_device cuda=mygpu:0` |

**坑位与排查**

1.  **驱动版本问题**：NVENC/NVDEC 功能与 NVIDIA 驱动版本强相关。日志中若出现 "The minimum required Nvidia driver for nvenc is..." 错误，请务必升级驱动。[[7]](https://ffmpeg.org/pipermail/ffmpeg-user/2021-November/053792.html)
2.  **像素格式不匹配**：硬件处理要求特定的像素格式。从 GPU 下载帧到 CPU 时，经常需要使用 `format` 滤镜指定一个兼容的格式（如 `nv12` 或 `yuv420p`）。错误日志通常会提示 "Impossible to convert between the formats supported by the filter"。
    ```bash
    # 错误示例：scale_cuda 输出 cuda 格式，但 fade 滤镜只接受软件格式
    # -vf "scale_cuda=1280:720,fade=in:0:30" 
    
    # 正确做法：先下载回 CPU 内存
    -vf "scale_cuda=1280:720,hwdownload,format=nv12,fade=in:0:30"
    ```

---

### 3.2 Intel Quick Sync Video (QSV)

QSV 是集成在 Intel CPU 核显中的专用视频处理单元。在 Linux 上通常通过 VAAPI 实现，而在 Windows 上则通过 D3D11VA 或 D3D9。FFmpeg 也提供了原生的 QSV 后端。[[43]](https://ffmpeg.org/general.html)

-   **通用解码选项**: `-hwaccel qsv`
-   **解码器**: `h264_qsv`, `hevc_qsv`, `av1_qsv` 等。
-   **编码器**: `h264_qsv`, `hevc_qsv`, `av1_qsv`。
-   **GPU 滤镜**: `scale_qsv`, `vpp_qsv` (功能更全的预处理滤镜)。

**关键选项与用法**

| 选项 (用于 `*_qsv` 编码器) | 用途 | 注意事项与示例 |
| :--- | :--- | :--- |
| `-init_hw_device qsv=...` | 初始化 QSV 设备。 | 在 Windows 上，可以指定 d3d11va 或 qsv。在 Linux 上，通常指向一个 VAAPI 设备。[[109]](https://superuser.com/questions/1704915/ffmpeg-h264-qsv-slower-than-libx264-real-time-buffer-too-full) <br> **Linux 示例**：`-init_hw_device vaapi=qsv:/dev/dri/renderD128` |
| `-hwaccel_output_format qsv` | 保持解码帧在 QSV 表面。 | 实现零拷贝 QSV 管线的关键。 |
| `-load_plugin <plugin>` | 加载特定的 QSV 插件。 | 例如 `hevc_hw` 以启用 HEVC 硬件编码。 <br> **示例**：`-load_plugin hevc_hw` |
| `-global_quality <值>` | 设置全局质量，类似于 CRF。 | 数值越小，质量越高。范围 1-51。是 `-c:v h264_qsv` 首选的质量控制模式。[[110]](https://stackoverflow.com/questions/61976567/hw-accel-transcode-intel-quick-sync-video-qsv-h264-qsv-and-crf-quality) <br> **示例**：`-global_quality 21` |
| `-preset <preset>` | 控制编码速度与质量。 | 可选值：`veryslow`, `slower`, `slow`, `medium` (默认), `fast`, `faster`, `veryfast`。 |

**坑位与排查**

1.  **环境与驱动**：在 Linux 上，需要正确安装 Intel Media Driver (`intel-media-va-driver-non-free`) 和 `vainfo` 工具。通过 `vainfo` 命令可以查看 QSV 是否被正确识别及其支持的 Profile。在 Windows 上，确保核显驱动已正确安装。
2.  **像素格式 `nv12` vs `qsv`**：QSV 内部处理通常使用 `nv12` 格式。当使用 `hwupload` 滤镜时，需先确保帧格式为 `nv12`。如果解码器输出 `qsv` 格式，则可以直接送入 `scale_qsv` 或 QSV 编码器。
    ```bash
    # 从软件帧上传到 QSV 进行缩放和编码
    -vf "format=nv12,hwupload=extra_hw_frames=64,scale_qsv=w=1280:h=720"
    ```
3.  **"No device available for QSV"**：此错误通常意味着驱动未正确安装，或者 FFmpeg 编译时没有启用 `libmfx`。确保 FFmpeg 构建时包含了 `--enable-libmfx`。[[43]](https://ffmpeg.org/general.html)

---

### 3.3 AMD (AMF / VAAPI)

AMD GPU 在 Windows 和 Linux 上提供硬件加速，主要通过两个框架：

1.  **AMF (Advanced Media Framework)**：AMD 官方的跨平台框架，在 Windows 上支持最完整。FFmpeg 通过 `h264_amf`, `hevc_amf`, `av1_amf` 编码器提供支持。[[38]](https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/FFmpeg-and-AMF-HW-Acceleration)
2.  **VAAPI (Video Acceleration API)**：Linux 通用的视频加速接口，AMD GPU 通过 Mesa 驱动提供支持。这是在 Linux 上使用 AMD 硬件加速的首选方式。

**3.3.1 AMF (主要在 Windows)**

-   **编码器**: `h264_amf`, `hevc_amf`, `av1_amf`
-   **解码**: 通常结合 DXVA2 或 D3D11VA 使用。`-hwaccel dxva2` 或 `-hwaccel d3d11va`。

**关键选项与用法 (`*_amf` 编码器)**

| 选项 | 用途 | 注意事项与示例 |
| :--- | :--- | :--- |
| `-quality <preset>` | 设置质量预设。 | 可选 `speed`, `balanced`, `quality`。[[37]](https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/Recommended-FFmpeg-Encoder-Settings) <br> **示例**：`-quality quality` |
| `-rc <mode>` | 设置码率控制模式。 | `cqp` (恒定 QP), `cbr`, `vbr`。配合 `cqp` 模式时，使用 `-qp_i`, `-qp_p`, `-qp_b` 分别设置 I/P/B 帧的量化参数。 |
| `-usage <usage>` | 编码用途。 | `transcoding`, `ultralowlatency`, `lowlatency`, `webcam`。 |

**3.3.2 VAAPI (Linux)**

-   **通用解码选项**: `-hwaccel vaapi`
-   **设备指定**: `-vaapi_device /dev/dri/renderDxxx`
-   **编码器**: `h264_vaapi`, `hevc_vaapi`
-   **GPU 滤镜**: `scale_vaapi`, `hwupload`

**坑位与排查 (AMF \u0026 VAAPI)**

1.  **驱动和库 (Linux)**：确保已安装 `mesa-va-drivers` 和 `vainfo`。使用 `vainfo` 检查 VAAPI 是否正常工作以及 GPU 支持的编解码 Profile。对于 AMF，可能需要安装 `amdgpu-pro` 驱动和对应的 AMF SDK。
2.  **设备路径 (Linux)**：`/dev/dri/renderDxxx` 节点是用于视频渲染的设备，必须正确指定。如果系统中有多个 GPU（例如 Intel 核显 + AMD 独显），需要通过此路径明确选择 AMD GPU。
3.  **像素格式 `nv12` (VAAPI)**：与 QSV 类似，VAAPI 管线也高度依赖 `nv12` 像素格式。在使用 `hwupload` 或 `scale_vaapi` 之前，通常需要先将视频帧转换为 `nv12`。[[58]](https://stackoverflow.com/questions/26000606/how-do-you-get-ffmpeg-to-encode-with-vaapi)

---

### 3.4 Apple (VideoToolbox)

在 macOS 和 iOS 设备上，FFmpeg 通过 VideoToolbox 框架利用内置的硬件编解码能力，包括 Apple Silicon (M1/M2/M3) 中的媒体引擎。[[25]](https://wiki.x266.mov/docs/encoders_hw/videotoolbox)

-   **通用解码选项**: `-hwaccel videotoolbox`
-   **编码器**: `h264_videotoolbox`, `hevc_videotoolbox`, `prores_videotoolbox`。
-   **解码器**: 自动通过 `-hwaccel videotoolbox` 启用。

**关键选项与用法 (`*_videotoolbox` 编码器)**

| 选项 | 用途 | 注意事项与示例 |
| :--- | :--- | :--- |
| `-b:v <比特率>` | 设置目标比特率。 | VideoToolbox 的主要码率控制方式之一。 |
| `-q:v <质量>` | **(已废弃)** 设置质量。 | 老版本中用于控制质量，新版本中 `-b:v` 或 `-profile` 更常用。 |
| `-profile:v <profile>` | 设置编码 Profile。 | 对于 H.264，可以是 `main`, `high`。对于 HEVC，可以是 `main`, `main10`。对于 ProRes，可以是 `proxy`, `lt`, `standard`, `hq`, `4444`, `4444xq`。[[25]](https://wiki.x266.mov/docs/encoders_hw/videotoolbox) <br> **示例**：`-profile:v high` |
| `-allow_sw <1或0>` | 是否允许在硬件编码不可用时回退到软件编码。 | 默认 `1` (允许)。设为 `0` 则在硬件不可用时报错退出。 |

**坑位与排查**

1.  **质量控制**：VideoToolbox 的质量控制不像 `libx264` 的 `-crf` 那样直观。通常需要通过调整 `-b:v` (比特率) 来平衡质量和文件大小。对于 HEVC，可以尝试 `-q:v` 选项（范围 1-100，越高越好），但这可能不适用于所有编码器。[[26]](https://stackoverflow.com/questions/64924728/optimally-using-hevc-videotoolbox-and-ffmpeg-on-osx)
2.  **不支持的像素格式**：如果 FFmpeg 日志显示 "Error submitting frame to Core Media..."，很可能是输入流的像素格式不被 VideoToolbox 直接支持。在编码前尝试添加 `-pix_fmt yuv420p` 或 `p010le` (10-bit) 滤镜进行转换。

---

### 3.5 Windows (DXVA2 / D3D11VA)

在 Windows 平台上，FFmpeg 主要通过 DirectX Video Acceleration (DXVA2) 和 Direct3D 11 Video API (D3D11VA) 来实现硬件解码。[[53]](https://learn.microsoft.com/en-us/windows/win32/medfound/about-dxva-2-0) 这两个是底层 API，通常与上层的 NVIDIA/Intel/AMD 驱动协同工作。

-   **解码选项**: `-hwaccel dxva2` 或 `-hwaccel d3d11va`。
-   **编码**: 通常不直接使用 DXVA2/D3D11VA 进行编码，而是调用特定厂商的编码器，如 `h264_nvenc` (NVIDIA), `hevc_qsv` (Intel), `av1_amf` (AMD)。

**用法**

DXVA2/D3D11VA 主要作为解码后端。当你想在 Windows 上实现完整的硬件加速管线时，流程如下：

1.  使用 `-hwaccel d3d11va` 和 `-hwaccel_output_format d3d11` 进行解码。
2.  解码后的 D3D11 表面（帧）可以直接被同样在 D3D11 上下文中运行的硬件编码器（如 `h264_nvenc`）或硬件滤镜使用，实现零拷贝。

**坑位与排查**

1.  **"Failed to create DirectX device"**：此错误通常指向显卡驱动问题或系统 DirectX 组件损坏。尝试更新显卡驱动和运行 `dxdiag` 进行诊断。
2.  **多 GPU 切换**：在拥有核显和独显的笔记本上，FFmpeg 默认可能使用核显。要强制使用独立显卡，可以尝试通过 `-init_hw_device` 指定设备索引。例如，为 NVENC 指定 GPU：
    ```bash
    -init_hw_device cuda=gpu:0 ... -c:v h264_nvenc
    ```
    或者在 Windows 图形设置中，为 `ffmpeg.exe` 指定“高性能”模式。

---

## 4. 线程与滤镜并发

FFmpeg 的多线程能力不仅限于编解码，还包括滤镜处理。理解并正确配置这些选项，对于最大化利用多核 CPU 至关重要。

### 4.1 过滤器线程模型

-   **简单滤镜 (`-vf`/`-af`)**: 由 `-filter_threads` 控制。它为每个简单的滤镜链创建一个线程池。如果一个滤镜链包含多个滤镜，它们仍在该链的线程池内运行。
-   **复杂滤镜 (`-filter_complex`)**: 由 `-filter_complex_threads` 控制。它为整个复杂的滤镜图创建一个全局线程池。这对于包含并行分支（例如，使用 `split` 或处理多个输入）的图尤其有效。::cite[3363]

**关键点**：

-   **切片线程 (Slice Threading)**：许多滤镜支持“切片线程”，即将单帧画面分割成多个水平切片，并由不同线程并行处理这些切片。这是 `-filter_threads` 和 `-filter_complex_threads` 发挥作用的主要机制。
-   **并非所有滤镜都支持多线程**：一些滤镜由于算法限制，本质上是单线程的。即使设置了多线程，它们也可能无法并行化。
-   **自动选择是好的开始**：默认情况下，FFmpeg 会将线程数设置为可用 CPU 核心数，这在大多数情况下是合理的起点。只有在确定滤镜是瓶颈时，才需要手动调整。

### 4.2 跨滤镜保持 GPU 帧

在进行硬件加速时，一个常见的性能陷阱是在多个滤镜之间不必要地将数据移入移出 GPU。

**正确的工作流**：

1.  **解码到 GPU**：`-hwaccel cuda -hwaccel_output_format cuda`
2.  **GPU 滤镜处理**：使用硬件原生的滤镜，如 `scale_cuda`、`scale_qsv`、`scale_vaapi`。
3.  **软件滤镜处理（如果必须）**：
    -   使用 `hwdownload` 将帧下载到系统内存。
    -   为了保证像素格式兼容，通常需要紧跟一个 `format` 滤镜，例如 `format=nv12`。
    -   应用你的软件滤镜（如 `drawtext`, `subtitles`）。
    -   如果后续还需要硬件处理（如硬件编码），则需要用 `hwupload` 重新上传回 GPU。
    
    ```bash
    # 一个完整的 GPU -> CPU -> GPU 流程示例
    -vf "scale_cuda=1280:720,hwdownload,format=nv12,drawtext=text='Hello':x=10:y=10,hwupload_cuda"
    ```
    这个流程引入了两次内存拷贝，应尽量避免。如果可能，寻找硬件版本的滤镜（例如，某些版本的 `overlay_cuda` 或 `drawtext` 的 OpenCL/Vulkan 实现）。

---

## 5. 诊断与可观测性

如何确认 FFmpeg 是否按照预期使用了硬件资源？以下是一些关键的诊断命令。

| 任务 | 命令 | 说明 |
| :--- | :--- | :--- |
| 列出所有可用的硬件加速方法 | `ffmpeg -hwaccels` | 显示当前 FFmpeg 构建版本支持的所有硬件加速 API，如 `cuda`, `dxva2`, `qsv` 等。::cite[2672] |
| 列出所有编码器 | `ffmpeg -encoders` | 详细列出所有支持的编码器，包括软件 (`libx264`) 和硬件 (`h264_nvenc`)。 |
| 列出所有解码器 | `ffmpeg -decoders` | 详细列出所有支持的解码器。 |
| 列出所有滤镜 | `ffmpeg -filters` | 显示所有可用的音视频滤镜，包括硬件滤镜（如 `scale_cuda`）。 |
| 确认硬件加速是否启用 | 在 FFmpeg 日志中查找 | - **解码**: 查找类似 "Using CUDA hardware acceleration" 或 "Using D3D11VA for hardware decoding" 的日志。<br>- **编码**: 查找编码器初始化的日志，例如 "[h264_nvenc ...]"。 <br>- **像素格式**: 观察滤镜链日志中的像素格式变化。`yuv420p` 通常是软件格式，而 `cuda`, `qsv`, `vaapi`, `d3d11` 等是硬件表面格式。 |
| 监控 GPU 使用率 | 使用系统工具 | - **NVIDIA**: `nvidia-smi dmon` 或 `nvidia-smi`。观察 `GPU-Util` 和 `ENC`/`DEC` 使用率。 <br>- **Intel**: `intel_gpu_top` (Linux)。<br>- **Windows**: 任务管理器的“性能”选项卡，选择 GPU 并查看“视频编码”和“视频解码”图表。 |
| 性能基准测试 | `-benchmark` 参数 | 在命令结尾添加此参数，FFmpeg 会在任务完成后报告总耗时和 CPU 占用，是衡量优化效果最直接的方法。 |

---

## 6. 高频实操配方

### 6.1 CPU 纯软件并发转码
```bash
ffmpeg -i input.mp4 \
       -c:v libx264 -preset fast -crf 22 \
       -c:a aac -b:a 128k \
       -threads 0 \
       -filter_complex "[0:v]scale=1280:720,split=2[out1][out2]" \
       -map "[out1]" -c:v libx264 -preset medium -crf 23 output_720p.mp4 \
       -map "[out2]" -c:v libx264 -preset fast -crf 24 output_480p.mp4
```
- **解读**：`-threads 0` 让 `libx264` 自动利用所有 CPU 核心。`-filter_complex` 使用了 `split` 将缩放后的流复制两份，分别进行不同参数的编码，实现了单输入、多输出的并行处理。

### 6.2 NVDEC+NVENC 单卡转码（保持帧在 GPU）
```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i input.mp4 \
       -vf "scale_cuda=1280:720" \
       -c:v hevc_nvenc -preset p5 -cq 24 \
       -c:a copy \
       output.mp4
```
- **解读**：`-hwaccel cuda -hwaccel_output_format cuda` 实现了硬件解码并将帧保留在 GPU。`scale_cuda` 在 GPU 上完成缩放。`hevc_nvenc` 直接从 GPU 显存中获取帧进行编码。这是最高效的 NVIDIA 硬件转码流程。::cite[240]

### 6.3 QSV/VAAPI 管线示例 (Linux)
```bash
ffmpeg -hwaccel vaapi -vaapi_device /dev/dri/renderD128 -hwaccel_output_format vaapi \
       -i input.mp4 \
       -vf "scale_vaapi=w=1920:h=1080:format=nv12" \
       -c:v h264_vaapi -qp 20 \
       -c:a copy \
       output_vaapi.mp4
```
- **解读**：通过 `-vaapi_device` 指定硬件设备。`-hwaccel_output_format vaapi` 确保解码帧是 VAAPI 表面。`scale_vaapi` 在 GPU 上缩放，并确保输出格式为 `nv12`，这是 `h264_vaapi` 编码器所期望的格式。[[61]](https://www.ffmpeg.media/articles/hardware-accelerated-ffmpeg-nvenc-vaapi-videotoolbox)

### 6.4 macOS VideoToolbox 示例
```bash
ffmpeg -i input.mov \
       -c:v hevc_videotoolbox -profile:v main -b:v 8M \
       -c:a aac -b:a 192k \
       output.mp4
```
- **解读**：在 macOS 上，通常不需要手动指定 `-hwaccel`。直接使用 `h264_videotoolbox` 或 `hevc_videotoolbox` 编码器，FFmpeg 会自动尝试使用硬件。质量通过 `-b:v` 控制。[[25]](https://wiki.x266.mov/docs/encoders_hw/videotoolbox)

### 6.5 多 GPU/多路转码的资源隔离示例
假设有两块 NVIDIA GPU，为两个独立的转码进程分别指定 GPU。

**进程 1 (使用 GPU 0):**
```bash
ffmpeg -hwaccel cuda -hwaccel_device 0 -i input1.mp4 \
       -c:v h264_nvenc -preset p5 output1.mp4
```

**进程 2 (使用 GPU 1):**
```bash
ffmpeg -hwaccel cuda -hwaccel_device 1 -i input2.mp4 \
       -c:v h264_nvenc -preset p5 output2.mp4
```
- **解读**：通过 `-hwaccel_device` 为每个 FFmpeg 进程绑定一个特定的 GPU，实现了资源隔离，避免了多进程争抢同一硬件导致性能下降。

---

## 快速自检清单

1.  **瓶颈在哪里？** 是 CPU（`top`/`htop` 100%）、GPU（`nvidia-smi`）、还是磁盘 I/O？
2.  **是否需要硬件加速？** 如果是，是否正确设置了 `-hwaccel` 和 `-hwaccel_output_format`？
3.  **帧是否保持在 GPU 中？** 检查滤镜链，避免不必要的 `hwdownload` 和 `hwupload`。
4.  **是否使用了与硬件匹配的滤镜？** （例如，用 `scale_cuda` 而非 `scale`）
5.  **线程数设置是否合理？** `-threads 0` 是好的开始。滤镜瓶颈时再调整 `-filter_threads`。
6.  **驱动和依赖是否最新？** 尤其是 NVIDIA 和 Intel 的驱动。
7.  **日志中是否有错误或警告？** 仔细阅读 FFmpeg 的输出，它通常会告诉你问题所在。
8.  **像素格式是否匹配？** 这是硬件加速中最常见的错误来源之一。
9.  **使用的是哪个 GPU？** 在多 GPU 系统中，确认 FFmpeg 使用了你期望的那个。
10. **命令是否以 `-benchmark` 结尾？** 量化你的优化效果。
