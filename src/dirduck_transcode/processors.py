from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from dirduck_transcode.media_types import is_image, is_video
from dirduck_transcode.models import TranscodeConfig


@dataclass(slots=True)
class FileProcessResult:
    kind: str
    action: str
    source_size: int
    output_size: int


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


def terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait()


def run_command(command: list[str], *, defer_interrupt: bool = False) -> None:
    """Run *command* in a subprocess, optionally deferring SIGINT until it completes.

    Signal handlers can only be installed from the main thread.  When called
    from a worker thread (e.g. inside a ``ThreadPoolExecutor``), the
    ``defer_interrupt`` mechanism is silently skipped and the function falls
    back to the regular ``KeyboardInterrupt`` path.
    """
    process = subprocess.Popen(command, start_new_session=True)
    interrupted = False
    original_handler: signal.Handlers | None = None

    can_handle_signals = threading.current_thread() is threading.main_thread()

    if defer_interrupt and can_handle_signals:
        def handle_interrupt(signum: int, frame: object | None) -> None:
            del signum, frame
            nonlocal interrupted
            interrupted = True
            print("Interrupt received. Waiting for current image to finish...")

        original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, handle_interrupt)

    try:
        while True:
            try:
                return_code = process.wait()
                break
            except KeyboardInterrupt:
                if defer_interrupt and can_handle_signals:
                    interrupted = True
                    continue
                terminate_process_group(process)
                raise
    finally:
        if original_handler is not None:
            signal.signal(signal.SIGINT, original_handler)

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    if interrupted:
        raise KeyboardInterrupt


def classify_file(path: Path) -> str:
    if is_video(path):
        return "video"
    if is_image(path):
        return "image"
    return "other"


def probe_fps(source: Path) -> float | None:
    """Return the average framerate of the first video stream, or None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=avg_frame_rate",
                "-of", "json",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        rate_str: str = data["streams"][0]["avg_frame_rate"]
        num, den = rate_str.split("/")
        if int(den) == 0:
            return None
        return int(num) / int(den)
    except (subprocess.TimeoutExpired, KeyError, IndexError, ValueError, ZeroDivisionError):
        return None


def transcode_video(source: Path, target: Path, config: TranscodeConfig) -> None:
    """Transcode a video file to HEVC using libx265 with thread-pool-based parallelism."""
    video_threads = max(1, config.processing_threads)
    x265_params = (
        f"pools={video_threads}:frame-threads={min(video_threads, 4)}"
        f":wpp=1:lookahead-slices=4"
    )
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
    if config.max_fps is not None:
        source_fps = probe_fps(source)
        if source_fps is not None and source_fps > config.max_fps:
            command.extend(["-r", str(config.max_fps)])
    command.extend(
        [
            "-c:v",
            "libx265",
            "-x265-params",
            x265_params,
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
    try:
        run_command(command)
    except KeyboardInterrupt:
        if target.exists():
            target.unlink()
        raise


def compress_image(source: Path, target: Path, config: TranscodeConfig) -> None:
    command = [
        "magick",
        str(source),
        "-quality",
        str(config.image_quality),
        str(target),
    ]
    run_command(command, defer_interrupt=True)


def image_fallback_target(source: Path, target: Path) -> Path:
    source_extension = source.suffix.lower()
    if not source_extension:
        return target.with_suffix(".png")
    return target.with_suffix(source_extension)


def process_file(source: Path, target: Path, config: TranscodeConfig) -> FileProcessResult:
    kind = classify_file(source)
    source_size = source.stat().st_size

    if kind == "video":
        print(f"Transcoding video: {source}")
        transcode_video(source, target, config)
        return FileProcessResult(
            kind=kind,
            action="transcoded",
            source_size=source_size,
            output_size=target.stat().st_size,
        )

    if kind == "image":
        print(f"Compressing image: {source}")
        try:
            compress_image(source, target, config)
            return FileProcessResult(
                kind=kind,
                action="compressed",
                source_size=source_size,
                output_size=target.stat().st_size,
            )
        except subprocess.CalledProcessError:
            fallback_target = image_fallback_target(source, target)
            if target.exists():
                target.unlink()
            if fallback_target.exists():
                print(f"Image conversion fallback target exists, skipping: {fallback_target}")
                return FileProcessResult(
                    kind=kind,
                    action="fallback_skipped_existing",
                    source_size=source_size,
                    output_size=fallback_target.stat().st_size,
                )
            print(f"Image conversion failed for JPG, copying original as fallback: {source}")
            shutil.copy2(source, fallback_target)
            return FileProcessResult(
                kind=kind,
                action="fallback_copied",
                source_size=source_size,
                output_size=fallback_target.stat().st_size,
            )

    print(f"Copying file: {source}")
    shutil.copy2(source, target)
    return FileProcessResult(
        kind=kind,
        action="copied",
        source_size=source_size,
        output_size=source_size,
    )
