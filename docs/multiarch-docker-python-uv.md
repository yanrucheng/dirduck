# Docker Multi-Arch Builds for Python with Buildx & uv

A concise reference for building `linux/amd64` and `linux/arm64` container images for Python 3.12 projects using Docker Buildx, multi-stage builds, and `uv`.

## Project Directory Layout

A recommended structure for a Python CLI or service using a `src` layout.

```text
/my-python-app
├── .dockerignore
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── src/
│   └── my_app/
│       ├── __init__.py
│       └── main.py
└── tests/
    └── ...
```

## Key Dockerfile Traits

- **Multi-stage:** A `builder` stage to install dependencies and a minimal `runtime` stage.
- **Cache-friendly Layering:** Copy `pyproject.toml` and `uv.lock` first, install dependencies, then copy `src`. This prevents re-installing dependencies on every code change.
- **Minimal Runtime:** Use a `-slim` base image for the final stage to reduce image size and attack surface.
- **Non-root User:** Create and switch to a dedicated non-root user for security.
- **Virtual Environment:** Create a virtual environment inside the image to isolate dependencies and make `PATH` updates clean.
- **Platform-Independent:** The Dockerfile is generic and works for any architecture (`amd64`, `arm64`). The target platform is specified at build time.
- **Clear Entrypoint/Cmd:** Use `ENTRYPOINT` or `CMD` to define how the application runs.
- **Environment Variables:** Set common variables like `PYTHONUNBUFFERED` and `PATH`.
- **Optional Healthcheck:** Add a `HEALTHCHECK` for services that need it.

## Example Dockerfile

This two-stage Dockerfile uses `uv` to manage dependencies and creates a minimal, secure runtime image.

```dockerfile
# ---- Builder Stage ----
# Installs dependencies into a virtual environment using uv
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv, the fast Python package installer
RUN pip install uv

# Create a virtual environment
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy only the dependency definitions and install them
# This layer is cached as long as the lock file doesn't change
COPY pyproject.toml uv.lock ./
RUN uv sync --system-deps

# Copy the application source code
COPY src/ ./src/

# ---- Runtime Stage ----
# Creates a minimal final image with a non-root user
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create a non-root user for security
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot
USER nonroot

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=nonroot:nonroot /app/.venv ./.venv

# Copy the application source code from the builder stage
COPY --from=builder --chown=nonroot:nonroot /app/src ./src

# Set environment variables for the runtime
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# (Optional) Expose a port if it's a web service
# EXPOSE 8000

# (Optional) Add a healthcheck for services
# HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
#   CMD [ "python", "-m", "my_app.health" ]

# Define the entrypoint for the container
ENTRYPOINT [ "python", "-m", "my_app.main" ]
```

## .dockerignore Essentials

Prevent unnecessary files from being included in the build context to speed up builds and avoid security risks.

```ignore
# Git
.git/
.gitignore

# Docker
.dockerignore
Dockerfile

# Python caches and virtual environments
__pycache__/
*.pyc
*.pyo
.venv/
venv/
env/

# IDE and OS files
.idea/
.vscode/
.DS_Store

# Test files
tests/
pytest.ini
.pytest_cache/
```

## Build Commands

### Local Development

First, create and switch to a `buildx` builder instance (one-time setup):
```bash
docker buildx create --name my-builder --use
docker buildx inspect --bootstrap
```

Build a single-architecture image and load it into the local Docker daemon:
```bash
# For Apple Silicon (arm64)
docker buildx build --platform linux/arm64 --load -t my-app:dev .

# For Intel (amd64)
docker buildx build --platform linux/amd64 --load -t my-app:dev .
```

Build a multi-arch image and push it directly to a container registry:
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag your-registry/my-app:1.0.0 \
  --push \
  .
```

### CI/CD Snippet

In a CI/CD pipeline (e.g., GitHub Actions), use remote caching to speed up builds.

```yaml
# .github/workflows/build-image.yml snippet
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Log in to Registry
  uses: docker/login-action@v3
  with:
    registry: your-registry
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}

- name: Build and push multi-arch image
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: true
    tags: |
      your-registry/my-app:${{ github.sha }}
      your-registry/my-app:latest
    cache-from: type=registry,ref=your-registry/my-app:build-cache
    cache-to: type=registry,ref=your-registry/my-app:build-cache,mode=max
```

## Notes

- **Distroless:** For even smaller and more secure images, consider using a `gcr.io/distroless/python3-debian12` base for the `runtime` stage. This requires copying only the necessary application files and dependencies, as distroless images contain no shell or package manager.
- **Testing:** After pushing a multi-arch image, test it on both `amd64` and `arm64` platforms to ensure full compatibility.
- **Reproducibility:** `uv.lock` is crucial. It pins the exact versions of all dependencies, ensuring that builds are deterministic and reproducible across different environments.
- **Security:** Always run containers as a **non-root user** and only copy the minimal set of required files into the final image.
```