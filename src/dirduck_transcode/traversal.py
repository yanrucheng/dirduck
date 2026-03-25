from __future__ import annotations

from pathlib import Path

from dirduck_transcode.media_types import replace_output_extension
from dirduck_transcode.models import TranscodeConfig
from dirduck_transcode.processors import process_file, verify_dependencies


def iterate_files(input_path: Path) -> list[Path]:
    return sorted(path for path in input_path.rglob("*") if path.is_file())


def print_config(config: TranscodeConfig) -> None:
    resolution_description = (
        f" and resolution-{config.short_side_px}p" if config.short_side_px is not None else ""
    )
    quality_description = (
        f" with image quality-{config.image_quality}" if config.image_quality != 85 else ""
    )
    print(
        f"Using input {config.input_path}, preset-{config.preset} and crf-{config.crf}"
        f"{resolution_description}{quality_description}"
    )
    print(f"Output path: {config.output_path}")


def run(config: TranscodeConfig) -> int:
    verify_dependencies()
    print_config(config)
    config.output_path.mkdir(parents=True, exist_ok=True)

    for file_path in iterate_files(config.input_path):
        if config.skip_keyword and config.skip_keyword in str(file_path):
            print(f"Skipping {file_path} as it contains {config.skip_keyword}")
            continue

        rel_path = file_path.relative_to(config.input_path)
        output_dir = (config.output_path / rel_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = replace_output_extension(output_dir / file_path.name)
        process_file(file_path, output_file, config)

    return 0
