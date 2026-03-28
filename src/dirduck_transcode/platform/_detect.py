"""Runtime platform detection — probes the OS, architecture, and ffmpeg capabilities."""

from __future__ import annotations

import platform
import subprocess
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
