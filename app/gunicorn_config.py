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

# Preloading must stay OFF with the eventlet worker.
# preload_app imports the application in the master process, BEFORE the eventlet
# worker monkey-patches the standard library. Sockets created during that import
# (psycopg2, redis) would then be unpatched blocking sockets inside a green-thread
# runtime — a known source of hangs with Flask-SocketIO.
preload_app = False
