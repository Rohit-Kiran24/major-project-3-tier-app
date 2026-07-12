"""
Configuration module — runtime credential fetching from AWS Secrets Manager.
Falls back to environment variables for local development (docker-compose).
"""

import os
import json
import boto3
from botocore.exceptions import ClientError


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Redis for SocketIO message queue (cross-instance pub/sub)
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

    # Database config — fetched from Secrets Manager or env vars
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 5432))
    DB_NAME = os.environ.get('DB_NAME', 'chatapp')
    DB_USER = os.environ.get('DB_USER', 'chatadmin')
    DB_PASS = os.environ.get('DB_PASS', 'localdev123')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        """Initialize config — fetch secrets from AWS if enabled."""
        use_secrets = os.environ.get('USE_SECRETS_MANAGER', 'false').lower() == 'true'

        if use_secrets:
            try:
                secret_name = os.environ.get('SECRET_NAME', 'three-tier-chat/db-credentials')
                region = os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1')

                client = boto3.client('secretsmanager', region_name=region)
                response = client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])

                Config.DB_USER = secret['username']
                Config.DB_PASS = secret['password']
                Config.DB_HOST = secret.get('host', Config.DB_HOST)
                Config.DB_PORT = int(secret.get('port', Config.DB_PORT))
                Config.DB_NAME = secret.get('dbname', Config.DB_NAME)

                app.logger.info("✅ Database credentials loaded from Secrets Manager")
            except ClientError as e:
                app.logger.error(f"❌ Failed to fetch secrets: {e}")
                raise
            except Exception as e:
                app.logger.error(f"❌ Unexpected error fetching secrets: {e}")
                raise

        # Build SQLAlchemy URI
        built_uri = (
            f"postgresql://{Config.DB_USER}:{Config.DB_PASS}"
            f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
        )
        # Allow full override via env var (used by pytest / SQLite in CI)
        Config.SQLALCHEMY_DATABASE_URI = os.environ.get(
            'SQLALCHEMY_DATABASE_URI', built_uri
        )
        app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
