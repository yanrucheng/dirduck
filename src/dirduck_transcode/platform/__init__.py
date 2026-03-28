"""Dynamic platform detection and hardware-aware video encode profile selection.

Each supported runtime environment maps to exactly one encode profile class so
that ffmpeg arguments can be tuned per-platform without side-effects:

  Platform                     Profile class            Encoder
  -------------------------    ----------------------   -------------------
  1. Intel chip Docker Linux   IntelDockerLinuxProfile   libx265 (software)
  2. Apple chip Docker Linux   AppleDockerLinuxProfile   libx265 (software)
  3. Intel chip native macOS   IntelMacNativeProfile     libx265 (software)
  4. Apple chip native macOS   AppleMacNativeProfile     hevc_videotoolbox

Typical usage::

    from dirduck_transcode.platform import detect_platform, select_encode_profile

    info = detect_platform()
    profile = select_encode_profile(info)
"""

from dirduck_transcode.platform._apple_docker_linux import AppleDockerLinuxProfile
from dirduck_transcode.platform._apple_mac_native import AppleMacNativeProfile
from dirduck_transcode.platform._base import VideoEncodeProfile
from dirduck_transcode.platform._detect import PlatformInfo, detect_platform
from dirduck_transcode.platform._intel_docker_linux import IntelDockerLinuxProfile
from dirduck_transcode.platform._intel_mac_native import IntelMacNativeProfile
from dirduck_transcode.platform._select import format_platform_summary, select_encode_profile

__all__ = [
    "AppleDockerLinuxProfile",
    "AppleMacNativeProfile",
    "IntelDockerLinuxProfile",
    "IntelMacNativeProfile",
    "PlatformInfo",
    "VideoEncodeProfile",
    "detect_platform",
    "format_platform_summary",
    "select_encode_profile",
]
