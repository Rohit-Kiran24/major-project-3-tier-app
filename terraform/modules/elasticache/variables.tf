variable "project_name" { type = string }
variable "subnet_group_name" { type = string }
variable "redis_sg_id" { type = string }
variable "node_type" { type = string; default = "cache.t3.micro" }
