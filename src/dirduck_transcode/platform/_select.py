"""Profile selection and startup logging."""

from __future__ import annotations

from dirduck_transcode.platform._apple_docker_linux import AppleDockerLinuxProfile
from dirduck_transcode.platform._apple_mac_native import AppleMacNativeProfile
from dirduck_transcode.platform._base import VideoEncodeProfile
from dirduck_transcode.platform._detect import PlatformInfo
from dirduck_transcode.platform._intel_docker_linux import IntelDockerLinuxProfile
from dirduck_transcode.platform._intel_mac_native import IntelMacNativeProfile


def select_encode_profile(info: PlatformInfo, *, force_software: bool = False) -> VideoEncodeProfile:
    """Choose the encode profile that matches the detected platform.

    Mapping:
      Docker + arm64/aarch64              -> AppleDockerLinuxProfile
      Docker + x86_64/other               -> IntelDockerLinuxProfile
      macOS  + arm64 + VT available       -> AppleMacNativeProfile  (unless force_software)
      macOS  + x86_64/other               -> IntelMacNativeProfile
      Anything else (unknown)             -> IntelDockerLinuxProfile (safe fallback)

    When *force_software* is ``True``, hardware-accelerated profiles are
    bypassed and the corresponding software profile is returned instead.
    """
    if info.in_docker:
        if info.arch in ("arm64", "aarch64"):
            return AppleDockerLinuxProfile()
        return IntelDockerLinuxProfile()

    if info.system == "Darwin":
        if (
            not force_software
            and info.arch == "arm64"
            and "videotoolbox" in info.available_hwaccels
            and "hevc_videotoolbox" in info.available_encoders
        ):
            return AppleMacNativeProfile()
        return IntelMacNativeProfile()

    return IntelDockerLinuxProfile()


def format_platform_summary(info: PlatformInfo, profile: VideoEncodeProfile) -> str:
    """Return a multi-line summary for startup logging."""
    from dirduck_transcode import __version__

    docker_label = " (Docker)" if info.in_docker else " (native)"
    lines = [
        f"dirduck v{__version__}",
        f"Platform: {info.system} {info.arch}{docker_label}",
        f"Available hwaccels: {', '.join(sorted(info.available_hwaccels)) or 'none'}",
        f"Selected encode profile: {profile.name}",
    ]
    return "\n".join(lines)
