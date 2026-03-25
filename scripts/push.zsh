#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-chengyanru/dirduck}"
version_file="${VERSION_FILE:-VERSION}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required."
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

amd64_tag="${project_version}-amd64"
arm64_tag="${project_version}-arm64"

docker push "${image_name}:${amd64_tag}"
docker push "${image_name}:${arm64_tag}"

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

docker manifest push "${image_name}:${project_version}"
docker manifest push "${image_name}:latest"

echo "Pushed images: ${image_name}:${amd64_tag}, ${image_name}:${arm64_tag}"
echo "Pushed manifests: ${image_name}:${project_version}, ${image_name}:latest"
