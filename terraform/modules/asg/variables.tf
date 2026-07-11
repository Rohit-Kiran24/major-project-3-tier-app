variable "project_name" { type = string }
variable "aws_region" { type = string }
variable "app_sg_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "target_group_arn" { type = string }
variable "instance_profile_name" { type = string }
variable "secret_name" { type = string }
variable "db_host" { type = string }
variable "redis_host" { type = string }
variable "docker_image" {
  type    = string
  default = "rohitkiran24/three-tier-chat:latest"
}
variable "instance_type" {
  type    = string
  default = "t2.micro"
}
variable "desired_capacity" {
  type    = number
  default = 1
}
variable "min_size" {
  type    = number
  default = 1
}
variable "max_size" {
  type    = number
  default = 3
}
