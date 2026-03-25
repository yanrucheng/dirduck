#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-chengyanru/dirduck}"
builder_name="${BUILDER_NAME:-dirduck-multiarch}"
version_file="${VERSION_FILE:-VERSION}"
mode="${1:-single}"
host_arch="$(uname -m)"

if [[ "$host_arch" == "x86_64" || "$host_arch" == "amd64" ]]; then
  default_platform="linux/amd64"
elif [[ "$host_arch" == "arm64" || "$host_arch" == "aarch64" ]]; then
  default_platform="linux/arm64"
else
  default_platform="linux/amd64"
fi

platform="${PLATFORM:-$default_platform}"
image_tag="${IMAGE_TAG:-dev}"

ensure_builder() {
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
}

build_one() {
  local target_platform="$1"
  local target_tag="$2"
  docker buildx build \
    --platform "$target_platform" \
    -t "${image_name}:${target_tag}" \
    --load \
    .
  echo "Built local image ${image_name}:${target_tag} for ${target_platform}"
}

read_version() {
  if [[ ! -f "$version_file" ]]; then
    echo "Version file not found: ${version_file}"
    exit 1
  fi
  local version_value
  version_value="$(tr -d '[:space:]' < "$version_file")"
  if [[ -z "$version_value" ]]; then
    echo "Version file is empty: ${version_file}"
    exit 1
  fi
  echo "$version_value"
}

build_release() {
  local project_version
  project_version="$(read_version)"
  local amd64_tag="${project_version}-amd64"
  local arm64_tag="${project_version}-arm64"

  build_one "linux/amd64" "$amd64_tag"
  build_one "linux/arm64" "$arm64_tag"

  docker manifest rm "${image_name}:${project_version}" >/dev/null 2>&1 || true
  docker manifest rm "${image_name}:latest" >/dev/null 2>&1 || true

  docker manifest create "${image_name}:${project_version}" \
    --amend "${image_name}:${amd64_tag}" \
    --amend "${image_name}:${arm64_tag}"
  docker manifest annotate "${image_name}:${project_version}" "${image_name}:${amd64_tag}" --os linux --arch amd64
  docker manifest annotate "${image_name}:${project_version}" "${image_name}:${arm64_tag}" --os linux --arch arm64

  docker manifest create "${image_name}:latest" \
    --amend "${image_name}:${amd64_tag}" \
    --amend "${image_name}:${arm64_tag}"
  docker manifest annotate "${image_name}:latest" "${image_name}:${amd64_tag}" --os linux --arch amd64
  docker manifest annotate "${image_name}:latest" "${image_name}:${arm64_tag}" --os linux --arch arm64

  echo "Built release images: ${image_name}:${amd64_tag}, ${image_name}:${arm64_tag}"
  echo "Created local manifest tags: ${image_name}:${project_version}, ${image_name}:latest"
}

ensure_builder

if [[ "$mode" == "single" ]]; then
  build_one "$platform" "$image_tag"
elif [[ "$mode" == "release" ]]; then
  build_release
else
  echo "Unsupported mode: ${mode}"
  echo "Usage: ./build.zsh [single|release]"
  exit 1
fi
