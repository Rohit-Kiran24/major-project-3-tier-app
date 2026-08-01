#!/bin/bash
# =============================================================================
# EC2 User Data Bootstrap Script
# Installs Docker, pulls the chat app image, and runs it with AWS config
# This file is rendered by Terraform's templatefile() function
# =============================================================================

# Deliberately NOT using `set -e`: a single transient failure (slow NAT, a
# mirror hiccup) must not abort the script before `docker run`. Each critical
# step retries and is logged instead.
set -uxo pipefail
exec > >(tee -a /var/log/user_data.log) 2>&1

echo "$(date) - Bootstrap starting"

# ---------- Install Docker ----------
# Only docker is installed here. The application talks to Secrets Manager with
# boto3 from inside the container, so the host does not need the AWS CLI —
# installing it was an extra failure point during boot.
dnf install -y docker || yum install -y docker

systemctl enable --now docker

# Wait for the Docker daemon to accept connections before using it.
for i in $(seq 1 30); do
  docker info >/dev/null 2>&1 && break
  echo "$(date) - waiting for docker daemon ($i/30)"
  sleep 2
done

usermod -aG docker ec2-user

# ---------- Pull the application image ----------
# Egress goes through the NAT instance/gateway, which may still be converging
# when this instance boots, so retry with backoff rather than failing outright.
for i in $(seq 1 10); do
  if docker pull ${docker_image}; then
    echo "$(date) - image pulled on attempt $i"
    break
  fi
  echo "$(date) - docker pull failed (attempt $i/10), retrying"
  sleep 15
done

# ---------- Run the container ----------
docker rm -f chat-app 2>/dev/null || true

docker run -d \
  --name chat-app \
  --restart unless-stopped \
  -p 5000:5000 \
  -e AWS_DEFAULT_REGION=${region} \
  -e SECRET_NAME=${secret_name} \
  -e DB_HOST=${db_host} \
  -e REDIS_HOST=${redis_host} \
  -e USE_SECRETS_MANAGER=true \
  ${docker_image}

echo "$(date) - Bootstrap finished; container state:"
docker ps -a --filter name=chat-app
