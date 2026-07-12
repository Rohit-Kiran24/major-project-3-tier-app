variable "project_name" {
  type = string
}

variable "db_name" {
  type    = string
  default = "chatapp"
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_subnet_group_name" {
  type = string
}

variable "db_sg_id" {
  type = string
}

variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "multi_az" {
  description = "Enable Multi-AZ (production). Disable for cost savings."
  type        = bool
  default     = false
}
