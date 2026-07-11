"""Gunicorn production server configuration."""

import os

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 1                    # Single worker for t2.micro
worker_class = "eventlet"      # Required for WebSocket support
worker_connections = 1000

# Timeouts
timeout = 120                  # WebSocket connections need longer timeouts
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"                # stdout
errorlog = "-"                 # stderr
loglevel = os.environ.get("LOG_LEVEL", "info")

# Process naming
proc_name = "three-tier-chat"

# Preload app for better memory usage
preload_app = True
