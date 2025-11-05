# --------- Builder Stage ---------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock* ./

# Install dependencies first (for better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# Copy the project source code
COPY . /app

# Install the project in non-editable mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-editable

# --------- Final Stage ---------
FROM python:3.11-slim

# Update package lists and install basic dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy source code from builder stage
COPY --from=builder --chown=app:app /app/src /code/src
COPY --from=builder --chown=app:app /app/migrations /code/migrations
COPY --from=builder --chown=app:app /app/src/alembic.ini /code/alembic.ini

# Ensure the virtual environment is in the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set default port (can be overridden by Render/Railway)
ENV PORT=8000

# Switch to the non-root user
USER app

# Set the working directory
WORKDIR /code

# Production command with gunicorn (Render/Railway compatible)
CMD sh -c "gunicorn src.app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}"

# -------- Dev command (uncomment for local development) --------
# CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
