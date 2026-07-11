###############################################################################
# SECRETS MANAGER MODULE — Runtime DB Credential Injection
#
# Eliminates hardcoded credentials. Flask app fetches these at startup
# via boto3, using the EC2 instance's IAM role.
###############################################################################

resource "random_password" "db_password" {
  length  = 24
  special = false # Avoid special chars that break connection strings
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/db-credentials"
  description             = "RDS database credentials for ${var.project_name}"
  recovery_window_in_days = 0 # Allow immediate deletion for dev (set 7+ for prod)

  tags = {
    Name = "${var.project_name}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = var.db_host
    port     = 5432
    dbname   = var.db_name
  })
}

# IAM Policy — allows EC2 instances to read this specific secret
resource "aws_iam_policy" "secrets_read" {
  name        = "${var.project_name}-secrets-read"
  description = "Allow reading DB credentials from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [aws_secretsmanager_secret.db_credentials.arn]
      }
    ]
  })
}

# IAM Role for EC2 instances
resource "aws_iam_role" "app_role" {
  name = "${var.project_name}-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-app-role"
  }
}

# Attach Secrets Manager read policy
resource "aws_iam_role_policy_attachment" "secrets_read" {
  role       = aws_iam_role.app_role.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# Attach CloudWatch agent policy (for monitoring)
resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Attach SSM policy (for Session Manager — replaces bastion)
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance Profile — attaches the role to EC2 instances
resource "aws_iam_instance_profile" "app_profile" {
  name = "${var.project_name}-app-profile"
  role = aws_iam_role.app_role.name
}
