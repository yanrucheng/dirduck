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

COPY pyproject.toml uv.lock README.md VERSION /app/
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

ENTRYPOINT ["python", "-m", "dirduck_transcode.cli"]
