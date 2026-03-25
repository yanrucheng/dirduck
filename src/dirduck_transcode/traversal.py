from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dirduck_transcode.media_types import replace_output_extension
from dirduck_transcode.models import TranscodeConfig
from dirduck_transcode.processors import process_file, verify_dependencies


@dataclass(slots=True)
class ProcessingStats:
    directories_discovered: int = 0
    files_discovered: int = 0
    files_processed: int = 0
    files_skipped_keyword: int = 0
    files_skipped_existing: int = 0
    files_copied: int = 0
    files_unchanged: int = 0
    videos_transcoded: int = 0
    images_compressed: int = 0
    images_fallback_copied: int = 0
    images_fallback_skipped_existing: int = 0
    video_input_bytes: int = 0
    video_output_bytes: int = 0
    image_input_bytes: int = 0
    image_output_bytes: int = 0


def iterate_files(input_path: Path) -> list[Path]:
    return sorted(path for path in input_path.rglob("*") if path.is_file())


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    display = float(value)
    for unit in units:
        if display < 1024 or unit == units[-1]:
            return f"{display:.2f} {unit}"
        display /= 1024
    return f"{display:.2f} TB"


def format_compression_rate(source_bytes: int, output_bytes: int) -> str:
    if source_bytes <= 0:
        return "n/a"
    rate = (1 - (output_bytes / source_bytes)) * 100
    return f"{rate:.2f}%"


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


def print_summary(stats: ProcessingStats) -> None:
    print("\n=== Processing summary ===")
    print(
        f"Directories discovered: {stats.directories_discovered}, "
        f"files discovered: {stats.files_discovered}, files processed: {stats.files_processed}"
    )
    print(
        f"Kept unchanged: {stats.files_unchanged} "
        f"(copied: {stats.files_copied}, existing-output skips: {stats.files_skipped_existing}, "
        f"keyword skips: {stats.files_skipped_keyword})"
    )
    print(
        f"Video transcoded: {stats.videos_transcoded}, "
        f"input: {format_bytes(stats.video_input_bytes)}, output: {format_bytes(stats.video_output_bytes)}, "
        f"compression rate: {format_compression_rate(stats.video_input_bytes, stats.video_output_bytes)}"
    )
    print(
        f"Image compressed: {stats.images_compressed}, "
        f"input: {format_bytes(stats.image_input_bytes)}, output: {format_bytes(stats.image_output_bytes)}, "
        f"compression rate: {format_compression_rate(stats.image_input_bytes, stats.image_output_bytes)}"
    )
    print(
        f"Image fallback: copied-original {stats.images_fallback_copied}, "
        f"skipped-existing {stats.images_fallback_skipped_existing}"
    )


def run(config: TranscodeConfig) -> int:
    verify_dependencies()
    print_config(config)
    config.output_path.mkdir(parents=True, exist_ok=True)
    stats = ProcessingStats()
    files = iterate_files(config.input_path)
    stats.files_discovered = len(files)
    stats.directories_discovered = len(
        {file_path.relative_to(config.input_path).parent for file_path in files}
    )

    for file_path in files:
        if config.skip_keyword and config.skip_keyword in str(file_path):
            print(f"Skipping {file_path} as it contains {config.skip_keyword}")
            stats.files_skipped_keyword += 1
            stats.files_unchanged += 1
            continue

        rel_path = file_path.relative_to(config.input_path)
        output_dir = (config.output_path / rel_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = replace_output_extension(output_dir / file_path.name)
        result = process_file(file_path, output_file, config)
        stats.files_processed += 1

        if result.action == "copied":
            stats.files_copied += 1
            stats.files_unchanged += 1
        elif result.action == "skipped_existing":
            stats.files_skipped_existing += 1
            stats.files_unchanged += 1
        elif result.action == "fallback_copied":
            stats.images_fallback_copied += 1
            stats.files_unchanged += 1
        elif result.action == "fallback_skipped_existing":
            stats.images_fallback_skipped_existing += 1
            stats.files_unchanged += 1

        if result.kind == "video" and result.action == "transcoded":
            stats.videos_transcoded += 1
            stats.video_input_bytes += result.source_size
            stats.video_output_bytes += result.output_size
        elif result.kind == "image" and result.action == "compressed":
            stats.images_compressed += 1
            stats.image_input_bytes += result.source_size
            stats.image_output_bytes += result.output_size

    print_summary(stats)

    return 0
