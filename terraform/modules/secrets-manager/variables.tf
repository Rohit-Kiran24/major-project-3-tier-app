variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "chatadmin"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "chatapp"
}

variable "db_host" {
  description = "RDS endpoint (populated after RDS creation)"
  type        = string
  default     = "pending"
}
