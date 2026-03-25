# dirduck-transcode

Batch transcode videos and images into smaller size while preserving the exact input folder structure.

## Requirements

- Python 3.12
- `ffmpeg`
- `magick` (ImageMagick CLI)
- `uv`

## Install

```bash
uv sync
```

## Usage

```bash
uv run dirduck-transcode \
  --input /path/to/input \
  --preset slow \
  --crf 31 \
  --shortsidepx 1080 \
  --image-quality 7 \
  --skip 原片
```

The output directory follows the existing zsh naming behavior:

```text
<input>_h265[_<shortside>p]_<preset>_crf<crf>[_imgQ<image-quality>]
```

## Docker

Build image:

```bash
docker buildx build --platform linux/arm64 --load -t chengyanru/dirduck:dev .
```

Build local image with the project script:

```bash
zsh ./scripts/local_build.zsh
```

Build versioned multi-arch local images:

```bash
zsh ./scripts/build.zsh
```

Push and create manifest tags:

```bash
zsh ./scripts/push.zsh
```

Detailed instructions are in `docs/build_guide.md`.

Run:

```bash
docker run --rm -v /path/to/media:/data chengyanru/dirduck \
  --input /data \
  --preset slow \
  --crf 31
```

With a local alias like:

```bash
drun='docker run -i --rm -v llm_cache:/root/.cache -v ~/.config/ai-album:/root/.config/ai-album -v ${PWD}:/t -w /t --env-file ~/.env'
```

you can run against a relative directory under the current working directory:

```bash
drun chengyanru/dirduck -i ./relative/path/to/target
```
