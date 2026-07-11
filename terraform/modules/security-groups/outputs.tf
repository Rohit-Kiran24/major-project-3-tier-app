output "alb_sg_id" {
  description = "Security group ID for ALB"
  value       = aws_security_group.alb.id
}

output "app_sg_id" {
  description = "Security group ID for App instances"
  value       = aws_security_group.app.id
}

output "db_sg_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.db.id
}

output "redis_sg_id" {
  description = "Security group ID for ElastiCache Redis"
  value       = aws_security_group.redis.id
}

output "bastion_sg_id" {
  description = "Security group ID for Bastion host"
  value       = var.deploy_bastion ? aws_security_group.bastion[0].id : null
}
