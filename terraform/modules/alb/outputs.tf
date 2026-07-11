output "alb_dns_name" {
  description = "DNS name of the ALB (use this to access the app)"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the ALB"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN of the target group for ASG attachment"
  value       = aws_lb_target_group.app.arn
}

output "alb_zone_id" {
  description = "Hosted zone ID of the ALB"
  value       = aws_lb.main.zone_id
}
