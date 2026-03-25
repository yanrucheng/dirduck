#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-chengyanru/dirduck}"
builder_name="${BUILDER_NAME:-dirduck-multiarch}"
version_file="${VERSION_FILE:-VERSION}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required."
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required."
  exit 1
fi

if [[ ! -f "$version_file" ]]; then
  echo "Version file not found: ${version_file}"
  exit 1
fi

project_version="$(tr -d '[:space:]' < "$version_file")"
if [[ -z "$project_version" ]]; then
  echo "Version file is empty: ${version_file}"
  exit 1
fi

if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
  docker buildx create --name "$builder_name" --driver docker-container --use >/dev/null
else
  docker buildx use "$builder_name" >/dev/null
fi

docker buildx inspect --bootstrap >/dev/null

docker buildx build \
  --platform "linux/amd64" \
  -t "${image_name}:${project_version}-amd64" \
  --load \
  .

docker buildx build \
  --platform "linux/arm64" \
  -t "${image_name}:${project_version}-arm64" \
  --load \
  .

echo "Built local images: ${image_name}:${project_version}-amd64, ${image_name}:${project_version}-arm64"
echo "Next: zsh ./scripts/push.zsh"
