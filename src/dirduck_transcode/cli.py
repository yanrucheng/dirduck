from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".ts", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass(slots=True)
class TranscodeConfig:
    input_path: Path
    preset: str
    crf: int
    skip_keyword: str
    short_side_px: int | None
    image_quality: int
    output_path: Path


def parse_args(argv: list[str] | None = None) -> TranscodeConfig:
    parser = argparse.ArgumentParser(
        prog="dirduck-transcode",
        description="Batch transcode videos and images into smaller files while preserving the input folder structure.",
        epilog=(
            "Example:\n"
            "  dirduck-transcode --input /data/media --preset slow --crf 31 --shortsidepx 1080 --image-quality 7\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="Input directory to process.")
    parser.add_argument("--preset", default="slow", help="FFmpeg libx265 preset.")
    parser.add_argument("--crf", type=int, default=31, help="FFmpeg CRF value for video compression.")
    parser.add_argument(
        "-s",
        "--skip",
        dest="skip_keyword",
        default="原片",
        help="Skip files and directories whose path contains this keyword.",
    )
    parser.add_argument(
        "--shortsidepx",
        type=int,
        default=None,
        help="Optional max pixel size for the short side in video scaling.",
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=7,
        help="ImageMagick quality value applied during image compression.",
    )
    args = parser.parse_args(argv)

    input_path = args.input.expanduser().resolve()
    if not input_path.exists() or not input_path.is_dir():
        parser.error("--input must point to an existing directory.")
    if args.shortsidepx is not None and args.shortsidepx <= 0:
        parser.error("--shortsidepx must be a positive integer.")
    if args.image_quality <= 0:
        parser.error("--image-quality must be greater than 0.")

    output_path = build_output_path(
        input_path=input_path,
        preset=args.preset,
        crf=args.crf,
        short_side_px=args.shortsidepx,
        image_quality=args.image_quality,
    )

    return TranscodeConfig(
        input_path=input_path,
        preset=args.preset,
        crf=args.crf,
        skip_keyword=args.skip_keyword,
        short_side_px=args.shortsidepx,
        image_quality=args.image_quality,
        output_path=output_path,
    )


def build_output_path(
    input_path: Path, preset: str, crf: int, short_side_px: int | None, image_quality: int
) -> Path:
    resolution_postfix = f"_{short_side_px}p" if short_side_px else ""
    quality_postfix = f"_imgQ{image_quality}" if image_quality != 7 else ""
    return input_path.with_name(
        f"{input_path.name}_h265{resolution_postfix}_{preset}_crf{crf}{quality_postfix}"
    )


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


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def replace_output_extension(path: Path) -> Path:
    if is_video(path):
        return path.with_suffix(".mp4")
    return path


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


def print_config(config: TranscodeConfig) -> None:
    resolution_description = (
        f" and resolution-{config.short_side_px}p" if config.short_side_px is not None else ""
    )
    quality_description = (
        f" with image quality-{config.image_quality}" if config.image_quality != 7 else ""
    )
    print(
        f"Using input {config.input_path}, preset-{config.preset} and crf-{config.crf}"
        f"{resolution_description}{quality_description}"
    )
    print(f"Output path: {config.output_path}")


def iterate_files(input_path: Path) -> list[Path]:
    return sorted(path for path in input_path.rglob("*") if path.is_file())


def run(config: TranscodeConfig) -> int:
    verify_dependencies()
    print_config(config)
    config.output_path.mkdir(parents=True, exist_ok=True)

    for file_path in iterate_files(config.input_path):
        path_text = str(file_path)
        if config.skip_keyword and config.skip_keyword in path_text:
            print(f"Skipping {file_path} as it contains {config.skip_keyword}")
            continue

        rel_path = file_path.relative_to(config.input_path)
        output_dir = (config.output_path / rel_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = replace_output_extension(output_dir / file_path.name)

        process_file(file_path, output_file, config)

    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        config = parse_args(argv)
        return run(config)
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}: {' '.join(error.cmd)}", file=sys.stderr)
        return error.returncode
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
