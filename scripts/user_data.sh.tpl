#!/bin/bash
# =============================================================================
# EC2 User Data Bootstrap Script
# Installs Docker, pulls the chat app image, and runs it with AWS config
# This file is rendered by Terraform's templatefile() function
# =============================================================================

set -e

# Update system and install Docker
yum update -y
yum install -y docker aws-cli
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Log startup
echo "$(date) - Starting chat app container" >> /var/log/user_data.log

# Pull and run the chat application container
docker pull ${docker_image}

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

echo "$(date) - Chat app container started successfully" >> /var/log/user_data.log
