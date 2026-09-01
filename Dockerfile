FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=8000

WORKDIR /app

# Install PostgreSQL libraries & build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependencies first for Docker caching
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install dependencies using uv
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-cache; \
    elif [ -f pyproject.toml ]; then \
        uv sync --no-install-project --no-cache; \
    elif [ -f requirements.txt ]; then \
        uv pip install --system --no-cache -r requirements.txt; \
    fi

# Copy full application code
COPY . .

# Setup entrypoint script & static directories
RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/staticfiles /app/media

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Default Web Server Command
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]