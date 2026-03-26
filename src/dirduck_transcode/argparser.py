from __future__ import annotations

import argparse
import os
from enum import Enum
from pathlib import Path

from dirduck_transcode.models import TranscodeConfig


class ResolutionPreset(Enum):
    P240 = ("240", 240)
    P360 = ("360", 360)
    P480 = ("480", 480)
    P720 = ("720", 720)
    P1080 = ("1080", 1080)
    P1440 = ("1440", 1440)
    P4K = ("4k", 2160)
    P8K = ("8k", 4320)

    def __init__(self, cli_value: str, short_side_px: int) -> None:
        self.cli_value = cli_value
        self.short_side_px = short_side_px


RESOLUTION_CHOICES = [preset.cli_value for preset in ResolutionPreset]
RESOLUTION_BY_CLI_VALUE = {preset.cli_value: preset for preset in ResolutionPreset}


def parse_args(argv: list[str] | None = None) -> TranscodeConfig:
    parser = argparse.ArgumentParser(
        prog="dirduck-transcode",
        description="Batch transcode videos and images into smaller files while preserving the input folder structure.",
        epilog=(
            "Example:\n"
            "  dirduck-transcode -i /data/media -od /data/output -p medium -c 32 -r 1080 -q 70 -s 原片\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        required=True,
        type=Path,
        help="Directory that contains files to transcode.",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-od",
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. If omitted, output path is derived from the input directory and encode settings.",
    )
    output_group.add_argument(
        "-o",
        "--output-parent-dir",
        type=Path,
        default=None,
        help="Optional parent directory for the derived output directory name.",
    )
    parser.add_argument(
        "-p",
        "--video-preset",
        default="medium",
        help="x265 preset for video encoding speed/efficiency tradeoff (for example: ultrafast, medium, slow).",
    )
    parser.add_argument(
        "-c",
        "--video-crf",
        type=int,
        default=32,
        help="x265 Constant Rate Factor for video quality and size; lower values keep higher quality.",
    )
    parser.add_argument(
        "-s",
        "--skip-keyword",
        dest="skip_keyword",
        default="原片",
        help="Skip files and folders when their path contains this text. System junk files are always skipped by default.",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        choices=RESOLUTION_CHOICES,
        default="1080",
        help="Target short-side resolution preset. Supported: 240, 360, 480, 720, 1080, 1440, 4k, 8k.",
    )
    parser.add_argument(
        "-q",
        "--image-quality",
        type=int,
        default=70,
        help="Image compression quality passed to ImageMagick (1-100, higher keeps better quality).",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=max(1, (os.cpu_count() or 1) - 1),
        help="Maximum processing threads for video transcoding. Default is CPU cores minus one.",
    )
    args = parser.parse_args(argv)

    input_path = args.input_dir.expanduser().resolve()
    if not input_path.exists() or not input_path.is_dir():
        parser.error("--input-dir must point to an existing directory.")
    if args.image_quality <= 0:
        parser.error("--image-quality must be greater than 0.")
    if args.image_quality > 100:
        parser.error("--image-quality must be less than or equal to 100.")
    if args.threads <= 0:
        parser.error("--threads must be greater than 0.")
    if args.output_dir is not None and args.output_dir.exists() and not args.output_dir.is_dir():
        parser.error("--output-dir must point to a directory path.")
    if (
        args.output_parent_dir is not None
        and args.output_parent_dir.exists()
        and not args.output_parent_dir.is_dir()
    ):
        parser.error("--output-parent-dir must point to a directory path.")
    resolution_preset = RESOLUTION_BY_CLI_VALUE.get(args.resolution)
    output_path = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else build_output_path(
            input_path=input_path,
            preset=args.video_preset,
            crf=args.video_crf,
            resolution=args.resolution,
            image_quality=args.image_quality,
            output_parent_dir=(
                args.output_parent_dir.expanduser().resolve()
                if args.output_parent_dir is not None
                else None
            ),
        )
    )

    return TranscodeConfig(
        input_path=input_path,
        preset=args.video_preset,
        crf=args.video_crf,
        skip_keyword=args.skip_keyword,
        short_side_px=resolution_preset.short_side_px if resolution_preset is not None else None,
        image_quality=args.image_quality,
        output_path=output_path,
        processing_threads=args.threads,
    )


def build_output_path(
    input_path: Path,
    preset: str,
    crf: int,
    resolution: str | None,
    image_quality: int,
    output_parent_dir: Path | None,
) -> Path:
    resolution_postfix = f"_{resolution}" if resolution else ""
    quality_postfix = f"_imgQ{image_quality}" if image_quality != 70 else ""
    output_dir_name = f"{input_path.name}_h265{resolution_postfix}_{preset}_crf{crf}{quality_postfix}"
    if output_parent_dir is not None:
        return output_parent_dir / output_dir_name
    return input_path.with_name(output_dir_name)
