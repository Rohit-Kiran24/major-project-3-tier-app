###############################################################################
# ROOT VARIABLES — All configurable parameters for the 3-Tier Architecture
###############################################################################

# ---------- General ----------
variable "project_name" {
  description = "Project name used for all resource naming"
  type        = string
  default     = "three-tier-chat"
}

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment tag (dev/staging/prod)"
  type        = string
  default     = "dev"
}

# ---------- Networking ----------
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "availability_zones" {
  type    = list(string)
  default = ["ap-south-1a", "ap-south-1b"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "database_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.5.0/24", "10.0.6.0/24"]
}

variable "use_nat_gateway" {
  description = "Use managed NAT Gateway ($33/mo) or NAT Instance ($8.5/mo)"
  type        = bool
  default     = false
}

# ---------- Security ----------
variable "deploy_bastion" {
  description = "Deploy bastion host (false = use SSM Session Manager instead)"
  type        = bool
  default     = false
}

variable "admin_ip" {
  description = "Your IP for bastion SSH access (x.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"
}

# ---------- Database ----------
variable "db_username" {
  type    = string
  default = "chatadmin"
}

variable "db_name" {
  type    = string
  default = "chatapp"
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS (doubles cost)"
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  type    = string
  default = "db.t3.micro"
}

# ---------- Compute ----------
variable "docker_image" {
  type    = string
  default = "rohitkiran24/three-tier-chat:latest"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "asg_desired" {
  type    = number
  default = 1
}

variable "asg_min" {
  type    = number
  default = 1
}

variable "asg_max" {
  type    = number
  default = 3
}

# ---------- Monitoring ----------
variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = "alerts@example.com"
}
