#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-chengyanru/dirduck}"
image_tag="${IMAGE_TAG:-latest}"
builder_name="${BUILDER_NAME:-dirduck-multiarch}"
platforms="linux/amd64,linux/arm64"

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
  --platform "$platforms" \
  -t "${image_name}:${image_tag}" \
  --push \
  .

echo "Published ${image_name}:${image_tag} for ${platforms}"
