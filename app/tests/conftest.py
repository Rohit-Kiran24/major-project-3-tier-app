"""
pytest configuration for the chat application test suite.

Sets up sys.path and environment variables BEFORE any app module is imported.
This is critical because Config reads env vars at class-definition time.
We also override SQLALCHEMY_DATABASE_URI to use SQLite so no PostgreSQL
instance is needed during CI or local unit testing.
"""
import sys
import os

# ── 1. Add app/ to import path ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── 2. Set all env vars BEFORE any app module is imported ────────────────────
# These prevent Config from attempting a real PostgreSQL / Secrets Manager call.
os.environ.setdefault('USE_SECRETS_MANAGER', 'false')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'test')
os.environ.setdefault('DB_USER', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('SECRET_KEY', 'ci-test-secret-key-not-for-production')
os.environ.setdefault('REDIS_HOST', 'localhost')

# Ops Console background tasks (metrics publisher, Redis spike listener) must not
# start during tests — they would loop forever against a Redis that isn't there.
os.environ.setdefault('OPS_BACKGROUND', 'false')

# ── 3. Force SQLite so pytest never touches PostgreSQL ───────────────────────
# Config.init_app() will build a postgresql:// URI from the env vars above,
# then the test fixture immediately overrides it with SQLite.
# We also set it here as an extra safeguard during module-level imports.
os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
