# VideoToolbox Quality Calibration Report

## Background

`dirduck-transcode` supports both software encoding (`libx265`) and hardware encoding
(`hevc_videotoolbox` on native macOS). The user-facing quality knob is a single CRF
value (0-51, lower = better), which maps directly to libx265's CRF parameter. For
VideoToolbox, this CRF must be translated to the encoder's `-q:v` parameter (1-100,
higher = better).

This document describes how the mapping function was derived empirically using
objective video quality metrics.

## Test Setup

| Item | Value |
|------|-------|
| Source file | `output.mp4` — 3840x2160, H.264 Main, 30fps, ~11 Mbps, 5 seconds |
| Output resolution | 1080p short-side (Lanczos scaling, `param0=3`) |
| Output framerate | 30 fps |
| Audio | stripped (`-an`) to isolate video quality |
| Platform | macOS, Apple Silicon (arm64) |
| FFmpeg | 7.x (`Lavf61.7.100 / Lavc61.19.101`) |
| libx265 | 4.1+1, preset `medium` |

### Pipeline

Both encoders received identical input after the same software scale filter:

```
ffmpeg -i source.mp4 \
       -vf "scale='if(lt(iw,ih),min(1080,iw),-2)':'if(lt(iw,ih),-2,min(1080,ih))':flags=lanczos:param0=3" \
       -r 30 \
       <encoder-specific args> \
       -an output.mp4
```

A lossless Y4M reference was produced at the same resolution and frame rate for
metric computation.

## Quality Metrics

Two standard full-reference metrics were used:

### PSNR (Peak Signal-to-Noise Ratio)

Measures per-pixel reconstruction error in decibels. Higher is better.
Computed via FFmpeg's built-in `psnr` filter:

```bash
ffmpeg -i reference.y4m -i encoded.mp4 -lavfi "psnr" -f null -
```

The reported `average` PSNR across all frames is used.

### SSIM (Structural Similarity Index)

Measures perceived structural similarity on a 0-1 scale. Higher is better.
More perceptually relevant than PSNR. Computed via FFmpeg's `ssim` filter:

```bash
ffmpeg -i reference.y4m -i encoded.mp4 -lavfi "ssim" -f null -
```

The reported `All` SSIM (average across Y, U, V planes and all frames) is used.

## Raw Results

### libx265 (software baseline)

| CRF | Size (KB) | PSNR (dB) | SSIM |
|-----|-----------|-----------|------|
| 18 | 1577 | 49.94 | 0.9949 |
| 23 | 772 | 47.63 | 0.9929 |
| 28 | 400 | 45.09 | 0.9896 |
| 32 | 247 | 42.93 | 0.9856 |
| 38 | 130 | 39.50 | 0.9759 |

### hevc_videotoolbox — initial mapping (`q = 100 - crf * 2`)

| CRF | VT q | Size (KB) | PSNR (dB) | SSIM | PSNR gap vs libx265 |
|-----|------|-----------|-----------|------|----------------------|
| 18 | 64 | 1142 | 46.85 | 0.9912 | **-3.08 dB** |
| 23 | 54 | 634 | 44.19 | 0.9868 | **-3.44 dB** |
| 28 | 44 | 408 | 41.93 | 0.9814 | **-3.16 dB** |
| 32 | 36 | 302 | 40.25 | 0.9762 | **-2.68 dB** |
| 38 | 24 | 196 | 37.50 | 0.9658 | **-2.00 dB** |

The old mapping produced consistently **2-3.5 dB lower PSNR** — visually
noticeable, confirming the user-reported quality degradation.

### hevc_videotoolbox — calibration sweep

Additional encodes at fixed `-q:v` values to build a quality-vs-bitrate curve:

| VT q | Size (KB) | PSNR (dB) | SSIM |
|------|-----------|-----------|------|
| 50 | 503 | 43.00 | 0.9841 |
| 55 | 713 | 44.75 | 0.9879 |
| 60 | 892 | 45.79 | 0.9897 |
| 65 | 1142 | 46.85 | 0.9912 |
| 70 | 1703 | 48.44 | 0.9932 |
| 75 | 2242 | 49.20 | 0.9938 |
| 80 | 3479 | 50.74 | 0.9951 |

## Regression

### Goal

Find a linear function `vt_q = a - b * crf` such that the VideoToolbox output
matches libx265 PSNR at every CRF level.

### Step 1 — Identify target VT q for each CRF

By interpolating the calibration sweep, find which `-q:v` produces the same PSNR
as `libx265 -crf`:

| CRF | libx265 PSNR target | Ideal VT q (interpolated) |
|-----|---------------------|--------------------------|
| 18 | 49.94 | ~77 |
| 23 | 47.63 | ~68 |
| 28 | 45.09 | ~57 |
| 32 | 42.93 | ~50 |
| 38 | 39.50 | ~31 |

### Step 2 — Least-squares linear fit

Data points `(crf, ideal_q)`: (18, 77), (23, 68), (28, 57), (32, 50), (38, 31).

Standard ordinary least-squares regression:

```
x_mean = (18 + 23 + 28 + 32 + 38) / 5 = 27.8
y_mean = (77 + 68 + 57 + 50 + 31) / 5 = 56.6

Sxx = sum((x - x_mean)^2) = 240.8
Sxy = sum((x - x_mean)(y - y_mean)) = -543.4

slope     = Sxy / Sxx = -2.257
intercept = y_mean - slope * x_mean = 119.3
```

Rounded to clean constants: **`vt_q = round(120 - crf * 2.2)`**, clamped to [1, 100].

### Step 3 — Verify fit

| CRF | Formula output | Ideal target | Error |
|-----|---------------|--------------|-------|
| 18 | 80 | 77 | +3 |
| 23 | 69 | 68 | +1 |
| 28 | 58 | 57 | +1 |
| 32 | 50 | 50 | 0 |
| 38 | 36 | 31 | +5 |

The slight positive bias means the VT encoder will be marginally more generous
than libx265 at the same CRF, which is preferable to the alternative (users
notice quality loss far more than quality surplus).

## Verification Encode

Final confirmation at the default CRF 32:

| Encoder | VT q | Size (KB) | PSNR (dB) | SSIM |
|---------|------|-----------|-----------|------|
| libx265 CRF=32 | — | 247 | 42.93 | 0.9856 |
| VT **old** mapping | 36 | 302 | 40.25 | 0.9762 |
| VT **new** mapping | 50 | 503 | 43.00 | 0.9841 |

The new mapping achieves **PSNR parity** with libx265 (43.00 vs 42.93 dB).

## Trade-offs

Hardware encoding is inherently less bit-efficient than software encoding.
Achieving the same visual quality requires more bits:

| CRF | libx265 size | VT (quality-matched) size | Size ratio |
|-----|-------------|--------------------------|------------|
| 32 | 247 KB | 503 KB | ~2.0x |

In exchange, VideoToolbox encodes **10-20x faster** by offloading to the Apple
Silicon media engine. This is the expected trade-off for hardware encoders and is
well-documented in FFmpeg literature.

## Implementation

The mapping function lives in `src/dirduck_transcode/platform.py`:

```python
def _crf_to_vt_quality(crf: int) -> int:
    return max(1, min(100, round(120 - crf * 2.2)))
```

It is called by `VideoToolboxProfile.build_encode_args()` to translate the
user-provided CRF into a `-q:v` value for `hevc_videotoolbox`.
