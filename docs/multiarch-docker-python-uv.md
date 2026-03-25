# Python Docker Multi-Arch Routine (Buildx + uv)

Standard workflow for new Python projects:

- local single-platform dev build
- local versioned multi-arch build artifacts
- manual push + manifest publish

Target platforms: `linux/amd64` and `linux/arm64`.

## Standard Layout

```text
/my-python-app
├── .dockerignore
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── VERSION
├── scripts/
│   ├── local_build.zsh
│   ├── build.zsh
│   └── push.zsh
└── src/
    └── my_app/
```

## Contract

- `VERSION` is the release source of truth.
- `scripts/local_build.zsh` builds one platform image for local testing.
- `scripts/build.zsh` reads `VERSION` and builds two local images:
  - `<version>-amd64`
  - `<version>-arm64`
- `scripts/push.zsh` pushes both arch tags, then publishes two manifest tags:
  - `<version>`
  - `latest`

## Dockerfile Baseline

Use a platform-independent multi-stage Dockerfile.

```dockerfile
FROM python:3.12-slim AS builder

ARG PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PIP_INDEX_URL=${PYPI_MIRROR} \
    UV_INDEX_URL=${PYPI_MIRROR}

WORKDIR /app

RUN pip install --no-cache-dir uv
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY src /app/src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g; s|security.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg imagemagick ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot

COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --from=builder --chown=nonroot:nonroot /app/src /app/src

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src"

USER nonroot

ENTRYPOINT ["python", "-m", "my_app.main"]
```

## .dockerignore Baseline

```ignore
.git/
.gitignore

.dockerignore
Dockerfile

__pycache__/
*.pyc
*.pyo
.venv/
venv/
env/

.idea/
.vscode/
.DS_Store

tests/
pytest.ini
.pytest_cache/
```

## Script Templates

### 1) scripts/local_build.zsh

Use for fast local dev image build.

```bash
#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-your-dockerhub-user/my-app}"
image_tag="${IMAGE_TAG:-dev}"
builder_name="${BUILDER_NAME:-my-app-multiarch}"
host_arch="$(uname -m)"

if [[ "$host_arch" == "x86_64" || "$host_arch" == "amd64" ]]; then
  default_platform="linux/amd64"
elif [[ "$host_arch" == "arm64" || "$host_arch" == "aarch64" ]]; then
  default_platform="linux/arm64"
else
  default_platform="linux/amd64"
fi

platform="${PLATFORM:-$default_platform}"

docker buildx inspect "$builder_name" >/dev/null 2>&1 || docker buildx create --name "$builder_name" --driver docker-container --use >/dev/null
docker buildx use "$builder_name" >/dev/null
docker buildx inspect --bootstrap >/dev/null

docker buildx build \
  --platform "$platform" \
  -t "${image_name}:${image_tag}" \
  --load \
  .
```

### 2) scripts/build.zsh

Use for local versioned multi-arch artifacts.

```bash
#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-your-dockerhub-user/my-app}"
builder_name="${BUILDER_NAME:-my-app-multiarch}"
version_file="${VERSION_FILE:-VERSION}"

project_version="$(tr -d '[:space:]' < "$version_file")"

docker buildx inspect "$builder_name" >/dev/null 2>&1 || docker buildx create --name "$builder_name" --driver docker-container --use >/dev/null
docker buildx use "$builder_name" >/dev/null
docker buildx inspect --bootstrap >/dev/null

docker buildx build --platform linux/amd64 -t "${image_name}:${project_version}-amd64" --load .
docker buildx build --platform linux/arm64 -t "${image_name}:${project_version}-arm64" --load .
```

### 3) scripts/push.zsh

Use only when ready to publish.

```bash
#!/bin/zsh
set -euo pipefail

image_name="${IMAGE_NAME:-your-dockerhub-user/my-app}"
version_file="${VERSION_FILE:-VERSION}"
project_version="$(tr -d '[:space:]' < "$version_file")"

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
```

## Operational Routine

### Step 0: Set version

```bash
echo "0.1.0" > VERSION
```

### Step 1: Local single-platform test

```bash
zsh ./scripts/local_build.zsh
```

### Step 2: Build local multi-arch release artifacts

```bash
zsh ./scripts/build.zsh
```

### Step 3: Publish when ready

```bash
zsh ./scripts/push.zsh
```

## Verification

Before push:

```bash
docker image inspect your-dockerhub-user/my-app:0.1.0-amd64 --format '{{.Architecture}}'
docker image inspect your-dockerhub-user/my-app:0.1.0-arm64 --format '{{.Architecture}}'
```

After push:

```bash
docker manifest inspect your-dockerhub-user/my-app:0.1.0
docker manifest inspect your-dockerhub-user/my-app:latest
```

## Rules

- Do not build manifests before arch tags are pushed.
- Keep Dockerfile platform-neutral; choose platform only at build time.
- Always build from `uv.lock` for reproducibility.
- Always run runtime container as non-root.
