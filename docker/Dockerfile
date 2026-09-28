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

# eventlet replaces the standard library's DNS resolver with its own green
# implementation, which cannot resolve container and VPC service names here:
# a lookup of the cache hostname times out after ~20 s while psycopg2 — a C
# extension eventlet never patches — resolves the database fine. The result is
# a silent loss of the pub/sub backplane with nothing in the log. This variable
# keeps eventlet on the system resolver and must be set before the worker boots.
ENV EVENTLET_NO_GREENDNS=yes

# Expose Flask port
EXPOSE 5000

# Health check for Docker and ECS
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run with Gunicorn + Eventlet for production WebSocket support
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
