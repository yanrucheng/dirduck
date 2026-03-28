"""Dynamic platform detection and hardware-aware video encode profile selection.

Supported runtime environments:
  1. Intel chip Linux Docker   → software encoding (libx265)
  2. Apple chip Linux Docker   → software encoding (libx265)
  3. Intel chip native macOS   → VideoToolbox hardware encoding
  4. Apple chip native macOS   → VideoToolbox hardware encoding

Hardware acceleration is preferred on native macOS; Docker containers fall back
to software encoding because the standard container runtime does not expose GPU
devices.
"""

from __future__ import annotations

import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    """Snapshot of the detected runtime environment."""

    system: str
    arch: str
    in_docker: bool
    available_hwaccels: frozenset[str]
    available_encoders: frozenset[str]


def _is_running_in_docker() -> bool:
    """Detect whether the process is running inside a Docker container."""
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            text = cgroup.read_text()
            if "docker" in text or "containerd" in text or "kubepods" in text:
                return True
    except OSError:
        pass
    return False


def _query_ffmpeg_hwaccels() -> frozenset[str]:
    """Return the set of hardware acceleration methods supported by the ffmpeg binary."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-hwaccels"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        accels: list[str] = []
        capture = False
        for line in result.stdout.splitlines():
            if "Hardware acceleration methods:" in line:
                capture = True
                continue
            if capture:
                name = line.strip()
                if name:
                    accels.append(name)
        return frozenset(accels)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return frozenset()


def _query_ffmpeg_encoders() -> frozenset[str]:
    """Return the set of encoder names available in the ffmpeg binary."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        encoders: list[str] = []
        capture = False
        for line in result.stdout.splitlines():
            if "------" in line:
                capture = True
                continue
            if capture:
                parts = line.split()
                if len(parts) >= 2:
                    encoders.append(parts[1])
        return frozenset(encoders)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return frozenset()


def detect_platform() -> PlatformInfo:
    """Probe the runtime environment and return a PlatformInfo snapshot."""
    return PlatformInfo(
        system=platform.system(),
        arch=platform.machine(),
        in_docker=_is_running_in_docker(),
        available_hwaccels=_query_ffmpeg_hwaccels(),
        available_encoders=_query_ffmpeg_encoders(),
    )


# ---------------------------------------------------------------------------
# Video encode profiles
# ---------------------------------------------------------------------------


class VideoEncodeProfile(ABC):
    """Base class that encapsulates all encoder-specific ffmpeg arguments."""

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
    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        """Return encoder-specific args placed after the filter/fps section."""

    def description(self, crf: int, preset: str, threads: int) -> str:
        """Return a one-line summary suitable for startup logging."""
        return f"{self.name} | encoder={self.encoder}"


class Libx265Profile(VideoEncodeProfile):
    """Software HEVC encoding via libx265 with full CRF and preset support."""

    @property
    def name(self) -> str:
        return "libx265 (software)"

    @property
    def encoder(self) -> str:
        return "libx265"

    def build_input_args(self) -> list[str]:
        return []

    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        video_threads = max(1, threads)
        x265_params = (
            f"pools={video_threads}:frame-threads={min(video_threads, 4)}"
            f":wpp=1:lookahead-slices=4"
        )
        return [
            "-c:v", "libx265",
            "-x265-params", x265_params,
            "-preset", preset,
            "-crf", str(crf),
            "-tag:v", "hvc1",
        ]

    def description(self, crf: int, preset: str, threads: int) -> str:
        return (
            f"{self.name} | preset={preset}, crf={crf}, "
            f"threads={threads}"
        )


def _crf_to_vt_quality(crf: int) -> int:
    """Map an x265-style CRF value (0-51, lower=better) to a VideoToolbox
    quality value (1-100, higher=better).

    This is a linear approximation.  CRF 0 → 100, CRF 51 → 1.
    """
    return max(1, min(100, round(100 - crf * 2)))


class VideoToolboxProfile(VideoEncodeProfile):
    """Hardware HEVC encoding via Apple VideoToolbox on macOS.

    Uses ``-hwaccel videotoolbox`` for hardware-accelerated decoding and
    ``hevc_videotoolbox`` for encoding.  The CRF value provided by the user
    is mapped to a VideoToolbox quality parameter (``-q:v``).
    """

    @property
    def name(self) -> str:
        return "hevc_videotoolbox (hardware)"

    @property
    def encoder(self) -> str:
        return "hevc_videotoolbox"

    def build_input_args(self) -> list[str]:
        return ["-hwaccel", "videotoolbox"]

    def build_encode_args(self, crf: int, preset: str, threads: int) -> list[str]:
        vt_quality = _crf_to_vt_quality(crf)
        return [
            "-c:v", "hevc_videotoolbox",
            "-q:v", str(vt_quality),
            "-profile:v", "main",
            "-tag:v", "hvc1",
        ]

    def description(self, crf: int, preset: str, threads: int) -> str:
        vt_quality = _crf_to_vt_quality(crf)
        return (
            f"{self.name} | crf={crf} → vt_quality={vt_quality}, "
            f"preset ignored (hardware encoder)"
        )


# ---------------------------------------------------------------------------
# Profile selection
# ---------------------------------------------------------------------------


def select_encode_profile(info: PlatformInfo) -> VideoEncodeProfile:
    """Choose the best available video encode profile for the detected platform.

    Selection rules:
      - Native macOS with VideoToolbox + hevc_videotoolbox → VideoToolboxProfile
      - Everything else (Linux, Docker, missing encoder)   → Libx265Profile
    """
    if (
        not info.in_docker
        and info.system == "Darwin"
        and "videotoolbox" in info.available_hwaccels
        and "hevc_videotoolbox" in info.available_encoders
    ):
        return VideoToolboxProfile()
    return Libx265Profile()


def format_platform_summary(info: PlatformInfo, profile: VideoEncodeProfile) -> str:
    """Return a multi-line summary for startup logging."""
    docker_label = " (Docker)" if info.in_docker else " (native)"
    lines = [
        f"Platform: {info.system} {info.arch}{docker_label}",
        f"Available hwaccels: {', '.join(sorted(info.available_hwaccels)) or 'none'}",
        f"Selected encode profile: {profile.name}",
    ]
    return "\n".join(lines)
