# The API service, worker and CLI image (ADR-001). Base images are pinned by digest;
# Dependabot proposes updates (docs/development/github-actions.md).
FROM python:3.14-slim@sha256:0b566a9f30a60730df33c26ac62dedb55393d8814645cd03543b67bf8987f3a1 AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependencies first, so a source change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.14-slim@sha256:0b566a9f30a60730df33c26ac62dedb55393d8814645cd03543b67bf8987f3a1
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY catalog ./catalog
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CATALOG_DIR=/app/catalog
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["saudi-api", "serve", "--host", "0.0.0.0", "--port", "8000"]
