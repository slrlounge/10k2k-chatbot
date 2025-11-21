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

# Copy application code (now includes 10K2Kv2/ since removed from .dockerignore)
COPY . .

# Copy ingestion directory explicitly (needed for Shell)
COPY ingestion/ /app/ingestion/

# Remove video files to keep image small (~3MB vs 81GB)
# Videos should already be excluded by .dockerignore, but clean up just in case
RUN if [ -d "/app/10K2Kv2" ]; then \
        find /app/10K2Kv2 -type f ! -name "*.txt" -delete 2>/dev/null || true && \
        find /app/10K2Kv2 -type d -empty -delete 2>/dev/null || true; \
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

