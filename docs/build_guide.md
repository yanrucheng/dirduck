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

## Build Script Modes

`build.zsh` supports two modes:

- `single`: build one local image for one platform
- `release`: read `./VERSION`, build both platforms, and create two local manifest tags

Run from repository root.

## Mode 1: Single-Platform Local Build

```bash
zsh ./build.zsh single
```

Defaults:

- platform: host-based (`linux/amd64` on Intel, `linux/arm64` on Apple Silicon)
- image tag: `dev`

Override:

```bash
PLATFORM=linux/amd64 IMAGE_TAG=debug IMAGE_NAME=chengyanru/dirduck zsh ./build.zsh single
```

## Mode 2: Versioned Multi-Arch Local Release Build

`release` mode does all of this automatically:

- read `<version>` from `./VERSION`
- build `linux/amd64` image as `<version>-amd64`
- build `linux/arm64` image as `<version>-arm64`
- create local manifest tag `<version>`
- create local manifest tag `latest`

Run:

```bash
zsh ./build.zsh release
```

Optional custom image name and version file:

```bash
IMAGE_NAME=your-dockerhub-user/dirduck VERSION_FILE=./VERSION zsh ./build.zsh release
```

## Verify Local Release Artifacts

```bash
docker images | grep dirduck
docker image inspect chengyanru/dirduck:0.1.0-amd64 --format '{{.Architecture}}'
docker image inspect chengyanru/dirduck:0.1.0-arm64 --format '{{.Architecture}}'
docker manifest inspect chengyanru/dirduck:0.1.0
docker manifest inspect chengyanru/dirduck:latest
```

## Manual Push to Docker Hub Later

`build.zsh` does not push. When ready, push arch-specific images first, then push both manifest tags.

```bash
docker push chengyanru/dirduck:0.1.0-amd64
docker push chengyanru/dirduck:0.1.0-arm64
```

Push both manifest tags:

```bash
docker manifest push chengyanru/dirduck:0.1.0
docker manifest push chengyanru/dirduck:latest
```

Verify on registry:

```bash
docker manifest inspect chengyanru/dirduck:0.1.0
docker manifest inspect chengyanru/dirduck:latest
```
