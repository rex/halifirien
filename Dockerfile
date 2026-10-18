# syntax=docker/dockerfile:1.7
# halifirien — one small image: uv-synced dependencies, the app, and the committed schema.
# Runs as a non-root user with nothing to write; no secrets are baked in (AWS credentials
# arrive as env from an ExternalSecret, only when publishing is switched on).

FROM python:3.13-slim AS runtime
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=
ARG APP_VERSION=dev
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --shell /usr/sbin/nologin --no-create-home app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY schema ./schema

ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_VERSION=$APP_VERSION

LABEL org.opencontainers.image.title="halifirien" \
      org.opencontainers.image.description="Pushes a live, public homelab status document to a static site." \
      org.opencontainers.image.source="https://github.com/rex/halifirien" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$GIT_COMMIT" \
      org.opencontainers.image.created="$BUILD_DATE"

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host \"$APP_HOST\" --port \"$APP_PORT\" --no-access-log"]
