# Production Dockerfile for FastAPI Backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn

# Copy application code (but .dockerignore excludes 10K2K v2/)
COPY . .

# Copy ingestion directory explicitly (needed for Shell)
# This works because ingestion/ is NOT in .dockerignore
COPY ingestion/ /app/ingestion/

# Temporarily remove 10K2K v2/ from .dockerignore context by copying before user switch
# We need to copy it before switching users, and COPY respects .dockerignore
# So we'll use a build arg or copy it explicitly
# Actually, we need to copy it in a way that bypasses .dockerignore
# The solution: Copy everything first, then selectively copy transcripts
RUN --mount=type=bind,source=.,target=/buildcontext \
    if [ -d "/buildcontext/10K2K v2" ]; then \
        find "/buildcontext/10K2K v2" -name "*.txt" -type f | while read file; do \
            rel_path="${file#/buildcontext/}"; \
            dir="/app/$(dirname "$rel_path")"; \
            mkdir -p "$dir"; \
            cp "$file" "/app/$rel_path"; \
        done; \
    fi

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Render will set PORT env var)
EXPOSE 8000

# Health check (uses PORT env var, defaults to 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, requests; port = os.getenv('PORT', '8000'); requests.get(f'http://localhost:{port}/health', timeout=5)" || exit 1

# Run with gunicorn for production (multiple workers)
# Render requires listening on $PORT environment variable
CMD sh -c "gunicorn serve:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 120"

