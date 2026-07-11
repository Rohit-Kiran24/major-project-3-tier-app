###############################################################################
# ELASTICACHE MODULE — Redis for WebSocket Pub/Sub
#
# Enables cross-instance message broadcasting. When User A sends a message
# on Instance-1, Redis pub/sub notifies Instance-2 to deliver it to User B.
###############################################################################

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.node_type
  num_cache_nodes      = 1 # Single node for cost savings
  port                 = 6379
  subnet_group_name    = var.subnet_group_name
  security_group_ids   = [var.redis_sg_id]
  parameter_group_name = "default.redis7"

  tags = {
    Name = "${var.project_name}-redis"
    Tier = "data"
  }
}
