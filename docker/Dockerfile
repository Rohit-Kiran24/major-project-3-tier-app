# Multi-stage Docker build for the Flask chat application
# Stage 1: Install dependencies
# Stage 2: Minimal runtime image

# ==================== BUILDER ====================
FROM python:3.11-slim AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==================== RUNTIME ====================
FROM python:3.11-slim

# Security: run as non-root user
RUN groupadd -r chatapp && useradd -r -g chatapp chatapp

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ .

# Set ownership
RUN chown -R chatapp:chatapp /app

# Switch to non-root user
USER chatapp

# Expose Flask port
EXPOSE 5000

# Health check for Docker and ECS
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run with Gunicorn + Eventlet for production WebSocket support
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
