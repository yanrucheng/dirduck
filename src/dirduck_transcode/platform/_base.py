"""Abstract base class for video encode profiles, plus shared filter helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VideoEncodeProfile(ABC):
    """Base class that encapsulates all encoder-specific ffmpeg arguments.

    One concrete subclass exists per target platform.  Modifying a profile
    only affects the platform it represents; other platforms are untouched.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable profile name for logging."""

    @property
    @abstractmethod
    def encoder(self) -> str:
        """FFmpeg encoder name (e.g. 'libx265', 'hevc_videotoolbox')."""

    @abstractmethod
    def build_input_args(self) -> list[str]:
        """Return extra args placed *before* ``-i`` (e.g. hwaccel flags)."""

    @abstractmethod
    def build_scale_filter(self, short_side_px: int | None) -> str | None:
        """Return a ``-vf`` scale filter string, or *None* if no scaling is needed."""

    @abstractmethod
    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        """Return encoder-specific args placed after the filter/fps section."""

    def description(self, crf: int, preset: str, threads: int) -> str:
        """Return a one-line summary suitable for startup logging."""
        return f"{self.name} | encoder={self.encoder}"


# ---------------------------------------------------------------------------
# Shared helpers used by concrete profile implementations
# ---------------------------------------------------------------------------


def short_side_expressions(short_side_px: int) -> tuple[str, str]:
    """Return ``(width_expr, height_expr)`` for conditional short-side scaling.

    The expressions ensure:
      - The short side is capped at *short_side_px* (never upscaled).
      - The long side is calculated to preserve the aspect ratio with even
        pixel alignment (``-2``).
      - Portrait and landscape orientations are handled automatically.
    """
    w = f"if(lt(iw,ih),min({short_side_px},iw),-2)"
    h = f"if(lt(iw,ih),-2,min({short_side_px},ih))"
    return w, h


def crf_to_vt_quality(crf: int) -> int:
    """Map an x265-style CRF value (0-51, lower=better) to a VideoToolbox
    quality value (1-100, higher=better).

    The coefficients were derived from a least-squares regression that
    matches PSNR output of ``libx265 -crf`` to ``hevc_videotoolbox -q:v``
    on a 4K->1080p test encode.  Representative calibration points:

        CRF 18 -> q 80   (~ libx265 PSNR 49.9 dB)
        CRF 23 -> q 69   (~ libx265 PSNR 47.6 dB)
        CRF 28 -> q 58   (~ libx265 PSNR 45.1 dB)
        CRF 32 -> q 50   (~ libx265 PSNR 42.9 dB)
        CRF 38 -> q 36   (~ libx265 PSNR 39.5 dB)
    """
    return max(1, min(100, round(120 - crf * 2.2)))
