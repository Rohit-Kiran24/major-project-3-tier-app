###############################################################################
# ALB MODULE — Application Load Balancer (Presentation Tier)
#
# Public-facing ALB that terminates traffic and distributes requests
# across App Tier EC2 instances in multiple AZs.
# HTTP listener by default. HTTPS config included but requires ACM cert.
###############################################################################

resource "aws_lb" "main" {
  #checkov:skip=CKV_AWS_91:Access logging requires dedicated S3 bucket — deferred to reduce cost in academic deployment
  #checkov:skip=CKV_AWS_150:Deletion protection disabled to allow easy teardown of academic environment
  #checkov:skip=CKV2_AWS_20:HTTP-to-HTTPS redirect deferred to Stage-II pending ACM certificate
  #checkov:skip=CKV2_AWS_28:WAF adds significant cost — out of scope for cost-constrained academic project
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.public_subnet_ids

  drop_invalid_header_fields = true
  enable_deletion_protection = false # Set true for production

  tags = {
    Name = "${var.project_name}-alb"
    Tier = "presentation"
  }
}

# Target Group — routes to Flask app on port 5000
resource "aws_lb_target_group" "app" {
  #checkov:skip=CKV_AWS_378:Internal ALB-to-app traffic uses HTTP — TLS termination at ALB planned for Stage-II
  name     = "${var.project_name}-app-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  # Sticky sessions for WebSocket affinity
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400 # 24 hours
    enabled         = true
  }

  health_check {
    path                = "/health"
    port                = "5000"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-app-tg"
  }
}

# HTTP Listener (port 80) — default for testing without SSL
resource "aws_lb_listener" "http" {
  #checkov:skip=CKV_AWS_2:HTTPS listener deferred to Stage-II pending ACM certificate
  #checkov:skip=CKV_AWS_103:TLS policy not applicable to HTTP listener — HTTPS deferred to Stage-II
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# =============================================================================
# HTTPS Listener (port 443) — UNCOMMENT when you have an ACM certificate
# =============================================================================
# resource "aws_lb_listener" "https" {
#   load_balancer_arn = aws_lb.main.arn
#   port              = 443
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
#   certificate_arn   = var.acm_certificate_arn
#
#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.app.arn
#   }
# }
#
# # HTTP to HTTPS redirect (replace the http listener above with this)
# resource "aws_lb_listener" "http_redirect" {
#   load_balancer_arn = aws_lb.main.arn
#   port              = 80
#   protocol          = "HTTP"
#
#   default_action {
#     type = "redirect"
#     redirect {
#       port        = "443"
#       protocol    = "HTTPS"
#       status_code = "HTTP_301"
#     }
#   }
# }
