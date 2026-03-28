"""Platform 4 — Apple chip native macOS: hardware HEVC encoding via VideoToolbox."""

from __future__ import annotations

from dirduck_transcode.platform._base import (
    VideoEncodeProfile,
    crf_to_vt_quality,
    short_side_expressions,
)


class AppleMacNativeProfile(VideoEncodeProfile):
    """Hardware HEVC encoding via Apple VideoToolbox on Apple Silicon macOS.

    The full pipeline stays on hardware surfaces for maximum throughput:

    * ``-hwaccel videotoolbox -hwaccel_output_format videotoolbox`` keeps
      decoded frames on hardware surfaces.
    * ``scale_vt`` performs resolution scaling directly on VideoToolbox
      surfaces without downloading to system memory.
    * ``hevc_videotoolbox`` encodes directly from hardware surfaces.

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
        """Return full zero-copy hwaccel args — always keep frames on VT surfaces."""
        return ["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox"]

    def build_scale_filter(self, short_side_px: int | None) -> str | None:
        """Return a VideoToolbox-native ``scale_vt`` filter string."""
        if short_side_px is None:
            return None
        w, h = short_side_expressions(short_side_px)
        return f"scale_vt=w='{w}':h='{h}'"

    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        vt_quality = crf_to_vt_quality(crf)
        return [
            "-c:v", "hevc_videotoolbox",
            "-q:v", str(vt_quality),
            "-allow_sw", "0",
            "-profile:v", "main",
            "-tag:v", "hvc1",
        ]

    def description(self, crf: int, preset: str, threads: int) -> str:
        vt_quality = crf_to_vt_quality(crf)
        return (
            f"{self.name} | crf={crf} -> vt_quality={vt_quality}, "
            f"preset ignored (hardware encoder)"
        )
