# ==============================================================================
# Production Dockerfile for Autonomous README Writer Agent
# Lightweight, multi-stage, rootless, enterprise-secure container image.
# ==============================================================================

FROM python:3.11-slim as base

# Set environment variables for deterministic Python execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install security updates and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY core/ ./core/
COPY main.py .
COPY server.py .
COPY test_readme_agent.py .
COPY README.md .
COPY .env.example .

# Create a non-privileged user for security compliance (Principle of Least Privilege)
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose web application port
EXPOSE 8000

# Health check to ensure orchestrator container is healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI production server with uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
