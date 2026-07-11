variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID to create security groups in"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs (for bastion SSH access)"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs (Application Tier)"
  type        = list(string)
}

variable "database_subnet_cidrs" {
  description = "Database subnet CIDRs (Data Tier)"
  type        = list(string)
}

variable "deploy_bastion" {
  description = "Deploy bastion host security group"
  type        = bool
  default     = false
}

variable "admin_ip" {
  description = "Admin IP for bastion SSH access (format: x.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"
}
