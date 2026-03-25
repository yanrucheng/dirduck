#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-chengyanru/dirduck}"
image_tag="${IMAGE_TAG:-dev}"
builder_name="${BUILDER_NAME:-dirduck-multiarch}"
host_arch="$(uname -m)"

if [[ "$host_arch" == "x86_64" || "$host_arch" == "amd64" ]]; then
  default_platform="linux/amd64"
elif [[ "$host_arch" == "arm64" || "$host_arch" == "aarch64" ]]; then
  default_platform="linux/arm64"
else
  default_platform="linux/amd64"
fi

platform="${PLATFORM:-$default_platform}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required."
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required."
  exit 1
fi

if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
  docker buildx create --name "$builder_name" --driver docker-container --use >/dev/null
else
  docker buildx use "$builder_name" >/dev/null
fi

docker buildx inspect --bootstrap >/dev/null

docker buildx build \
  --platform "$platform" \
  -t "${image_name}:${image_tag}" \
  --load \
  .

echo "Built local image ${image_name}:${image_tag} for ${platform}"
