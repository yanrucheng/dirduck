# Multi-Arch Local Build Guide

This guide focuses on local multi-arch builds first, then manual Docker Hub push later.

## Project Version Source

Project release version is stored in:

```text
./VERSION
```

Example:

```text
0.1.0
```

## One-Time Buildx Setup

```bash
docker buildx create --name dirduck-multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

If already created:

```bash
docker buildx use dirduck-multiarch
docker buildx inspect --bootstrap
```

## Scripts

The repository provides three scripts in `./scripts`:

- `local_build.zsh`: build one local image for one platform
- `build.zsh`: build both local arch images using `<version>` from `./VERSION`
- `push.zsh`: push arch images, create/push manifest tags `<version>` and `latest`

Run from repository root.

## 1) Single-Platform Local Build

```bash
zsh ./scripts/local_build.zsh
```

Defaults:

- platform: host-based (`linux/amd64` on Intel, `linux/arm64` on Apple Silicon)
- image tag: `dev`

Override:

```bash
PLATFORM=linux/amd64 IMAGE_TAG=debug IMAGE_NAME=chengyanru/dirduck zsh ./scripts/local_build.zsh
```

## 2) Versioned Multi-Arch Local Build

`scripts/build.zsh` does all of this automatically:

- read `<version>` from `./VERSION`
- build `linux/amd64` image as `<version>-amd64`
- build `linux/arm64` image as `<version>-arm64`

Run:

```bash
zsh ./scripts/build.zsh
```

Optional custom image name and version file:

```bash
IMAGE_NAME=your-dockerhub-user/dirduck VERSION_FILE=./VERSION zsh ./scripts/build.zsh
```

## Verify Local Release Artifacts

```bash
docker images | grep dirduck
docker image inspect chengyanru/dirduck:0.1.0-amd64 --format '{{.Architecture}}'
docker image inspect chengyanru/dirduck:0.1.0-arm64 --format '{{.Architecture}}'
```

## 3) Push and Create Manifests

`scripts/push.zsh` does all of this:

- push `<version>-amd64` and `<version>-arm64`
- create manifest `<version>` from the two arch tags
- create manifest `latest` from the two arch tags
- push both manifest tags

```bash
zsh ./scripts/push.zsh
```

Optional custom image name and version file:

```bash
IMAGE_NAME=your-dockerhub-user/dirduck VERSION_FILE=./VERSION zsh ./scripts/push.zsh
```

Verify on registry after push:

```bash
docker manifest inspect chengyanru/dirduck:0.1.0
docker manifest inspect chengyanru/dirduck:latest
```
