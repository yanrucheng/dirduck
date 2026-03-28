"""Platform 4 — Apple chip native macOS: hardware HEVC encoding via VideoToolbox."""

from __future__ import annotations

from dirduck_transcode.platform._base import (
    VideoEncodeProfile,
    crf_to_vt_quality,
    short_side_expressions,
)


class AppleMacNativeProfile(VideoEncodeProfile):
    """Hardware HEVC encoding via Apple VideoToolbox on Apple Silicon macOS.

    Pipeline layout:

    * ``-hwaccel videotoolbox`` enables hardware-accelerated H.264/HEVC
      decoding via the Apple media engine.  Decoded frames are automatically
      transferred to system memory so they can pass through software filters
      without compatibility issues.
    * A Lanczos ``scale`` filter handles resolution changes in software.
      Using the software scaler (instead of ``scale_vt``) avoids a known
      ffmpeg limitation where mid-stream colour-parameter changes trigger
      filter-graph reconfiguration that fails when the graph contains
      hardware-surface filters (``Impossible to convert between …
      'Parsed_scale_vt_0' and 'auto_scale_0'``).
    * ``hevc_videotoolbox`` encodes the frames on the Apple media engine.
      The encoder transparently uploads CPU frames to hardware; the decode
      + encode path still runs at ~6 × real-time on M-series chips.

    The CRF value provided by the user is mapped to a VideoToolbox quality
    parameter (``-q:v``).
    """

    @property
    def name(self) -> str:
        return "hevc_videotoolbox (Apple Mac native)"

    @property
    def encoder(self) -> str:
        return "hevc_videotoolbox"

    def build_input_args(self) -> list[str]:
        """Return hwaccel args for VideoToolbox decode with CPU-accessible frames."""
        return ["-hwaccel", "videotoolbox"]

    def build_scale_filter(self, short_side_px: int | None) -> str | None:
        """Return a Lanczos-based software scale filter string."""
        if short_side_px is None:
            return None
        w, h = short_side_expressions(short_side_px)
        return f"scale='{w}':'{h}':flags=lanczos:param0=3"

    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        vt_quality = crf_to_vt_quality(crf)
        return [
            "-c:v", "hevc_videotoolbox",
            "-q:v", str(vt_quality),
            "-allow_sw", "0",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main",
            "-tag:v", "hvc1",
        ]

    def description(self, crf: int, preset: str, threads: int) -> str:
        vt_quality = crf_to_vt_quality(crf)
        return (
            f"{self.name} | crf={crf} -> vt_quality={vt_quality}, "
            f"preset ignored (hardware encoder)"
        )
