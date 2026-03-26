from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TranscodeConfig:
    input_path: Path
    preset: str
    crf: int
    skip_keyword: str
    short_side_px: int | None
    image_quality: int
    output_path: Path
    processing_threads: int
