# Multi-stage build (PROPOSAL §12.1): the builder installs dependencies with uv;
# the runtime image holds only the virtualenv and the code, and runs as a non-root user.

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv
# Compile .pyc at build time; copy files instead of hard-linking across layers.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
# --frozen: install exactly what uv.lock says; fail if the lock is out of date.
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 netdesk
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY app ./app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER netdesk
EXPOSE 8000
# Migrate, then serve. Render sets PORT; locally it defaults to 8000.
# --forwarded-allow-ips '*': trust X-Forwarded-For from Render's proxy (not 127.0.0.1),
# so per-IP rate limits see the real client. Safe only because the container is
# reachable through that proxy alone.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
