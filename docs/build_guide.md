# dirduck Multi-Arch Docker Build Guide

This project follows a multi-architecture Docker design for `linux/amd64` and `linux/arm64` using Docker Buildx, a multi-stage Dockerfile, and `uv`.

## What Is Implemented

- Multi-stage Dockerfile with `builder` and `runtime` stages
- Dependency locking with `uv.lock` during image build
- Layer-cached dependency installation before copying source code
- Minimal runtime image with non-root user
- Buildx-based multi-arch publish flow in `build.zsh`

## Prerequisites

- Docker with Buildx enabled
- Access to a container registry (for push)

Verify Buildx:

```bash
docker buildx version
```

## Buildx One-Time Setup

Create and bootstrap a dedicated builder:

```bash
docker buildx create --name dirduck-multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

If the builder already exists:

```bash
docker buildx use dirduck-multiarch
docker buildx inspect --bootstrap
```

## Local Single-Architecture Build

Use `--load` to import the image into your local Docker daemon.

Apple Silicon local build:

```bash
docker buildx build --platform linux/arm64 --load -t chengyanru/dirduck:dev .
```

Intel local build:

```bash
docker buildx build --platform linux/amd64 --load -t chengyanru/dirduck:dev .
```

## Multi-Architecture Publish

Use the included script:

```bash
zsh ./build.zsh
```

With custom image/tag:

```bash
IMAGE_NAME=your-registry/dirduck IMAGE_TAG=v1.0.0 zsh ./build.zsh
```

The script publishes a manifest list for:

- `linux/amd64`
- `linux/arm64`

## Manual Multi-Architecture Publish

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag your-registry/dirduck:v1.0.0 \
  --push \
  .
```

## CI/CD

The repository includes a GitHub Actions workflow at `.github/workflows/build-image.yml`.

It builds and pushes `linux/amd64` + `linux/arm64` images using Buildx with remote registry cache.

Required repository secrets:

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

## Run Example

```bash
docker run --rm -v /path/to/media:/data chengyanru/dirduck:latest \
  --input /data \
  --preset slow \
  --crf 31
```

## Validation Checklist

- Confirm the image manifest contains both `amd64` and `arm64`
- Run the image on each architecture
- Confirm `ffmpeg` and `magick` are available in runtime
- Confirm container starts as non-root user
