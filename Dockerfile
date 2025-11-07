# --------- Builder Stage ---------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock* ./

# Install dependencies first (for better layer caching)
# Try to install with ML support, but continue if tflite-runtime unavailable
RUN --mount=type=cache,target=/root/.cache/uv \
    (uv sync --no-install-project --extra ml || uv sync --no-install-project) || true

# Copy the project source code
COPY . /app

# Install the project in non-editable mode
# Try with ML support first, fallback to regular install
RUN --mount=type=cache,target=/root/.cache/uv \
    (uv sync --no-editable --extra ml || uv sync --no-editable) || true

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
COPY --from=builder --chown=app:app /app/src/migrations /code/migrations
COPY --from=builder --chown=app:app /app/src/alembic.ini /code/alembic.ini
COPY --from=builder --chown=app:app /app/deploy.sh /code/deploy.sh

# Ensure the virtual environment is in the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set default port (can be overridden by Render/Railway)
ENV PORT=8000

# Make deployment script executable
RUN chmod +x /code/deploy.sh

# Switch to the non-root user
USER app

# Set the working directory
WORKDIR /code

# Use deployment script to run migrations then start server
CMD ["/code/deploy.sh"]

# -------- Dev command (uncomment for local development) --------
# CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
