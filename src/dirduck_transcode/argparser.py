from __future__ import annotations

import argparse
from pathlib import Path

from dirduck_transcode.models import TranscodeConfig


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

    return TranscodeConfig(
        input_path=input_path,
        preset=args.preset,
        crf=args.crf,
        skip_keyword=args.skip_keyword,
        short_side_px=args.shortsidepx,
        image_quality=args.image_quality,
        output_path=build_output_path(
            input_path=input_path,
            preset=args.preset,
            crf=args.crf,
            short_side_px=args.shortsidepx,
            image_quality=args.image_quality,
        ),
    )


def build_output_path(
    input_path: Path, preset: str, crf: int, short_side_px: int | None, image_quality: int
) -> Path:
    resolution_postfix = f"_{short_side_px}p" if short_side_px else ""
    quality_postfix = f"_imgQ{image_quality}" if image_quality != 7 else ""
    return input_path.with_name(
        f"{input_path.name}_h265{resolution_postfix}_{preset}_crf{crf}{quality_postfix}"
    )
