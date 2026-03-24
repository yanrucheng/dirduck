# Local Docker Build Guide

Use this guide to build a local image for `dirduck` quickly.

## Default Build

Run from repository root:

```bash
zsh ./build.zsh
```

This builds and loads a local image:

- image: `chengyanru/dirduck:dev`
- platform: `linux/arm64`

## Script Options

Override defaults with environment variables:

```bash
IMAGE_NAME=chengyanru/dirduck IMAGE_TAG=dev PLATFORM=linux/arm64 zsh ./build.zsh
```

Available variables:

- `IMAGE_NAME` default: `chengyanru/dirduck`
- `IMAGE_TAG` default: `dev`
- `PLATFORM` default: `linux/arm64`
- `BUILDER_NAME` default: `dirduck-multiarch`

For Intel target build on Apple Silicon:

```bash
PLATFORM=linux/amd64 zsh ./build.zsh
```

## Verify Local Image

```bash
docker images | grep dirduck
```

Run:

```bash
docker run --rm -v /path/to/media:/data chengyanru/dirduck:dev \
  --input /data \
  --preset slow \
  --crf 31
```

## Push to Docker Hub

Push is manual and not handled by `build.zsh`.

After local verification:

```bash
docker tag chengyanru/dirduck:dev chengyanru/dirduck:latest
docker push chengyanru/dirduck:latest
```
