from __future__ import annotations

from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".ts", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def replace_output_extension(path: Path) -> Path:
    if is_video(path):
        return path.with_suffix(".mp4")
    return path
