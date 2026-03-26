from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from dirduck_transcode.media_types import is_image, is_video, replace_output_extension
from dirduck_transcode.models import TranscodeConfig
from dirduck_transcode.processors import process_file, verify_dependencies

DEFAULT_SYSTEM_SKIP_EXACT_NAMES = frozenset(
    {
        ".DS_Store",
        ".Spotlight-V100",
        ".TemporaryItems",
        ".Trashes",
        ".fseventsd",
        "Thumbs.db",
        "Desktop.ini",
        "Icon\r",
        "__MACOSX",
    }
)
DEFAULT_SYSTEM_SKIP_PREFIXES = ("._",)
IMAGE_PARALLEL_WORKERS = 4


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


def should_skip_system_name(name: str) -> bool:
    return name in DEFAULT_SYSTEM_SKIP_EXACT_NAMES or name.startswith(
        DEFAULT_SYSTEM_SKIP_PREFIXES
    )


def iterate_files(input_path: Path) -> list[Path]:
    files: list[Path] = []
    for root, dir_names, file_names in input_path.walk(on_error=lambda _: None):
        dir_names[:] = [name for name in dir_names if not should_skip_system_name(name)]
        for name in file_names:
            if should_skip_system_name(name):
                continue
            files.append(root / name)
    return sorted(files)


def canonical_output_extension(path: Path) -> str | None:
    """Return the canonical output extension for a media input file."""
    if is_video(path):
        return ".mp4"
    if is_image(path):
        return ".jpg"
    return None


def build_collision_safe_target(
    source: Path, base_target: Path, reserved_targets: set[Path]
) -> Path:
    """Create a unique output target by appending the source's original type."""
    type_token = source.suffix.lower().lstrip(".") or "file"
    base_name = f"{base_target.stem}-{type_token}"
    candidate = base_target.with_name(f"{base_name}{base_target.suffix}")
    index = 2
    while candidate in reserved_targets:
        candidate = base_target.with_name(f"{base_name}-{index}{base_target.suffix}")
        index += 1
    return candidate


def plan_output_paths(files: list[Path], config: TranscodeConfig) -> dict[Path, Path]:
    """Plan output paths to prevent collisions after extension normalization."""
    sources_by_target: dict[Path, list[Path]] = {}

    for file_path in files:
        rel_path = file_path.relative_to(config.input_path)
        output_dir = (config.output_path / rel_path.parent).resolve()
        base_target = replace_output_extension(output_dir / file_path.name)
        sources_by_target.setdefault(base_target, []).append(file_path)

    resolved_by_source: dict[Path, Path] = {}
    reserved_targets: set[Path] = set()

    for base_target, sources in sources_by_target.items():
        if len(sources) == 1:
            resolved_target = base_target
            if resolved_target in reserved_targets:
                resolved_target = build_collision_safe_target(
                    sources[0], base_target, reserved_targets
                )
            resolved_by_source[sources[0]] = resolved_target
            reserved_targets.add(resolved_target)
            continue

        canonical_sources = [
            source
            for source in sources
            if canonical_output_extension(source) == source.suffix.lower()
        ]
        if canonical_sources:
            primary_source = min(canonical_sources)
        else:
            primary_source = min(sources)

        primary_target = base_target
        if primary_target in reserved_targets:
            primary_target = build_collision_safe_target(
                primary_source, base_target, reserved_targets
            )
        resolved_by_source[primary_source] = primary_target
        reserved_targets.add(primary_target)

        for source in sorted(sources):
            if source == primary_source:
                continue
            unique_target = build_collision_safe_target(source, base_target, reserved_targets)
            resolved_by_source[source] = unique_target
            reserved_targets.add(unique_target)

    return resolved_by_source


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
        f" with image quality-{config.image_quality}" if config.image_quality != 70 else ""
    )
    print(
        f"Using input {config.input_path}, preset-{config.preset} and crf-{config.crf}"
        f"{resolution_description}{quality_description}"
    )
    print(f"Output path: {config.output_path}")
    print(f"Video threads: {config.processing_threads}")


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


def print_existing_skip_batch(paths: list[Path]) -> None:
    count = len(paths)
    if count == 0:
        return
    print(f"Skipping {count} existing files:")
    if count <= 6:
        display_paths = paths
    else:
        display_paths = [*paths[:2], Path("..."), *paths[-2:]]
    for path in display_paths:
        print(f"  {path}")


def apply_result_to_stats(stats: ProcessingStats, result) -> None:
    stats.files_processed += 1
    if result.action == "copied":
        stats.files_copied += 1
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


def process_images_in_parallel(
    image_tasks: list[tuple[Path, Path]], config: TranscodeConfig, stats: ProcessingStats
) -> None:
    if not image_tasks:
        return
    worker_count = IMAGE_PARALLEL_WORKERS
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(process_file, source, target, config): (source, target)
            for source, target in image_tasks
        }
        for future in as_completed(future_map):
            result = future.result()
            apply_result_to_stats(stats, result)


def run(config: TranscodeConfig) -> int:
    verify_dependencies()
    print_config(config)
    config.output_path.mkdir(parents=True, exist_ok=True)
    stats = ProcessingStats()
    files = iterate_files(config.input_path)
    output_paths = plan_output_paths(files, config)
    stats.files_discovered = len(files)
    stats.directories_discovered = len(
        {file_path.relative_to(config.input_path).parent for file_path in files}
    )
    existing_skip_batch: list[Path] = []
    video_tasks: list[tuple[Path, Path]] = []
    image_tasks: list[tuple[Path, Path]] = []
    other_tasks: list[tuple[Path, Path]] = []

    for file_path in files:
        if config.skip_keyword and config.skip_keyword in str(file_path):
            print_existing_skip_batch(existing_skip_batch)
            existing_skip_batch.clear()
            print(f"Skipping {file_path} as it contains {config.skip_keyword}")
            stats.files_skipped_keyword += 1
            stats.files_unchanged += 1
            continue

        rel_path = file_path.relative_to(config.input_path)
        output_dir = (config.output_path / rel_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_paths[file_path]
        if output_file.exists():
            existing_skip_batch.append(output_file)
            stats.files_skipped_existing += 1
            stats.files_unchanged += 1
            continue
        kind = "other"
        if is_video(file_path):
            kind = "video"
        elif is_image(file_path):
            kind = "image"
        if kind == "video":
            video_tasks.append((file_path, output_file))
        elif kind == "image":
            image_tasks.append((file_path, output_file))
        else:
            other_tasks.append((file_path, output_file))

    print_existing_skip_batch(existing_skip_batch)

    if video_tasks and image_tasks:
        print("Scheduling policy: mixed input detected, pause image processing while videos run.")
    elif image_tasks and not video_tasks:
        print(f"Scheduling policy: pure image input, run up to {IMAGE_PARALLEL_WORKERS} images in parallel.")

    for file_path, output_file in video_tasks:
        result = process_file(file_path, output_file, config)
        apply_result_to_stats(stats, result)

    process_images_in_parallel(image_tasks, config, stats)

    for file_path, output_file in other_tasks:
        result = process_file(file_path, output_file, config)
        apply_result_to_stats(stats, result)

    print_summary(stats)

    return 0
