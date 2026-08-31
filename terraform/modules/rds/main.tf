###############################################################################
# RDS MODULE — PostgreSQL in Isolated Subnets (Data Tier)
#
# Multi-AZ toggleable for cost optimization.
# Zero internet access — enforced by isolated subnet route table.
###############################################################################

resource "aws_db_instance" "main" {
  #checkov:skip=CKV_AWS_118:Enhanced monitoring requires dedicated IAM role — basic monitoring sufficient for academic workload
  #checkov:skip=CKV_AWS_161:IAM authentication not used — credentials managed via Secrets Manager with instance-profile access
  #checkov:skip=CKV_AWS_293:Deletion protection disabled to allow easy teardown of academic environment
  #checkov:skip=CKV_AWS_354:Performance Insights uses default encryption — CMK adds cost with no benefit for academic workload
  #checkov:skip=CKV2_AWS_69:App-to-DB traffic stays within isolated VPC subnets — TLS in transit deferred to Stage-II
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = var.instance_class

  allocated_storage     = 20
  max_allocated_storage = 50 # Auto-scale storage up to 50GB
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  multi_az             = var.multi_az
  db_subnet_group_name = var.db_subnet_group_name

  vpc_security_group_ids = [var.db_sg_id]
  publicly_accessible    = false # CRITICAL: zero public access

  backup_retention_period      = 7
  copy_tags_to_snapshot        = true
  auto_minor_version_upgrade   = true
  performance_insights_enabled = true
  skip_final_snapshot          = true # Set false for production

  enabled_cloudwatch_logs_exports = ["postgresql"]

  parameter_group_name = aws_db_parameter_group.main.name

  tags = {
    Name = "${var.project_name}-db"
    Tier = "data"
  }
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-pg-params"
  family = "postgres15"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "${var.project_name}-pg-params"
  }
}
