from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from dirduck_transcode.media_types import is_image, is_video
from dirduck_transcode.models import TranscodeConfig


def verify_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required but was not found in PATH.")
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick (magick) is required but was not found in PATH.")


def scale_filter(short_side_px: int | None) -> str | None:
    if short_side_px is None:
        return None
    return (
        f"scale='if(lt(iw,ih),min({short_side_px},iw),-2)':"
        f"'if(lt(iw,ih),-2,min({short_side_px},ih))':flags=lanczos:param0=3"
    )


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def transcode_video(source: Path, target: Path, config: TranscodeConfig) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-i",
        str(source),
    ]
    filter_arg = scale_filter(config.short_side_px)
    if filter_arg:
        command.extend(["-vf", filter_arg])
    command.extend(
        [
            "-c:v",
            "libx265",
            "-preset",
            config.preset,
            "-crf",
            str(config.crf),
            "-tag:v",
            "hvc1",
            "-c:a",
            "copy",
            str(target),
            "-y",
        ]
    )
    run_command(command)


def compress_image(source: Path, target: Path, config: TranscodeConfig) -> None:
    command = [
        "magick",
        str(source),
        "-quality",
        str(config.image_quality),
        str(target),
    ]
    run_command(command)


def process_file(source: Path, target: Path, config: TranscodeConfig) -> None:
    if target.exists():
        print(f"Output file already exists, skipping: {target}")
        return

    if is_video(source):
        print(f"Transcoding video: {source}")
        transcode_video(source, target, config)
        return

    if is_image(source):
        print(f"Compressing image: {source}")
        compress_image(source, target, config)
        return

    print(f"Copying file: {source}")
    shutil.copy2(source, target)
