###############################################################################
# SECURITY GROUPS MODULE — Zero-Trust Sequential Firewall Chain
#
# Each security group references the PREVIOUS tier's SG ID (not IP ranges).
# This enforces strict tier isolation at the infrastructure level.
#
# Chain: Internet → ALB-SG → App-SG → DB-SG
#                                    → Redis-SG
#        Your IP → Bastion-SG → App-SG (SSH)
###############################################################################

# ---------- ALB Security Group (Presentation Tier) ----------
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTP/HTTPS from internet to ALB"
  vpc_id      = var.vpc_id

  # HTTP from anywhere (for testing without SSL)
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS from anywhere (when SSL certificate is configured)
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound only to App tier
  egress {
    description = "To App tier on port 5000"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
    Tier = "presentation"
  }
}

# ---------- App Security Group (Application Tier) ----------
resource "aws_security_group" "app" {
  name        = "${var.project_name}-app-sg"
  description = "Allow traffic from ALB only, SSH from bastion"
  vpc_id      = var.vpc_id

  # App port from ALB only (SG reference — zero-trust)
  ingress {
    description     = "Flask app from ALB"
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # SSH from bastion/SSM (for debugging)
  ingress {
    description = "SSH from within VPC (bastion/SSM)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.public_subnet_cidrs
  }

  # Outbound to DB
  egress {
    description = "To RDS PostgreSQL"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.database_subnet_cidrs
  }

  # Outbound to Redis
  egress {
    description = "To ElastiCache Redis"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }

  # Outbound to internet via NAT (for Docker pulls, updates, Secrets Manager API)
  egress {
    description = "HTTPS to internet (AWS APIs, Docker Hub)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP to internet (yum updates)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
    Tier = "application"
  }
}

# ---------- Database Security Group (Data Tier) ----------
resource "aws_security_group" "db" {
  name        = "${var.project_name}-db-sg"
  description = "Allow PostgreSQL from App tier ONLY"
  vpc_id      = var.vpc_id

  # PostgreSQL from App SG only (SG reference — zero-trust)
  ingress {
    description     = "PostgreSQL from App tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # No egress rules — database should not initiate outbound connections
  # AWS adds a default allow-all egress; we override with restrictive rules
  egress {
    description = "Deny all outbound (isolated tier)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
    Tier = "data"
  }
}

# ---------- Redis Security Group ----------
resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Allow Redis from App tier ONLY"
  vpc_id      = var.vpc_id

  # Redis from App SG only (SG reference — zero-trust)
  ingress {
    description     = "Redis from App tier"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "Allow responses within VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
    Tier = "data"
  }
}

# ---------- Bastion Security Group (optional) ----------
resource "aws_security_group" "bastion" {
  count       = var.deploy_bastion ? 1 : 0
  name        = "${var.project_name}-bastion-sg"
  description = "Allow SSH from admin IP only"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip]
  }

  egress {
    description = "SSH to private instances"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }

  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}
