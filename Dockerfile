# syntax=docker/dockerfile:1

# Use a specific Python version for stability
ARG PYTHON_VERSION=3.13.7
FROM python:${PYTHON_VERSION}-slim

# 1. Environment Variables
# Prevents Python from writing pyc files and ensures logs are not buffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Path Configuration
# We add the uv binary location and the virtual environment to the system PATH
# This fixes the "/bin/sh: 1: uv: not found" error
ENV PATH="/uv/bin:/app/.venv/bin:$PATH"

WORKDIR /app

# 3. Install uv
# We copy the 'uv' binary from the official image directly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/

# 4. Install Dependencies
# We use cache mounts to speed up the build and bind mounts to avoid extra layers
# This looks for your pyproject.toml and uv.lock files
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# 5. Copy Source Code
# Copy the rest of your files (like manage.py, config/, utils/, etc.)
COPY . .

# 6. Final Setup
# Expose the port Waitress will listen on
EXPOSE 8000

# Run the application using Waitress
# Pointing to 'config.wsgi:application' matches your folder structure
CMD ["waitress-serve", "--port=8000", "config.wsgi:application"]