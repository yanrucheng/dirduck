"""Platform 1 — Intel chip Docker Linux: software HEVC encoding via libx265."""

from __future__ import annotations

from dirduck_transcode.platform._base import VideoEncodeProfile, short_side_expressions


class IntelDockerLinuxProfile(VideoEncodeProfile):
    """Software HEVC encoding for x86-64 Docker containers on Linux."""

    @property
    def name(self) -> str:
        return "libx265 (Intel Docker Linux)"

    @property
    def encoder(self) -> str:
        return "libx265"

    def build_input_args(self) -> list[str]:
        return []

    def build_scale_filter(self, short_side_px: int | None) -> str | None:
        if short_side_px is None:
            return None
        w, h = short_side_expressions(short_side_px)
        return f"scale='{w}':'{h}':flags=lanczos:param0=3"

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
