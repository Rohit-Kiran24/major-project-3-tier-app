###############################################################################
# ROOT main.tf — Composes all modules into the 3-Tier Architecture
#
# Module dependency chain:
# VPC → Security Groups → Secrets Manager → RDS → ElastiCache → ALB → ASG → Monitoring
###############################################################################

# ======================== PHASE 2: NETWORKING ========================
module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  use_nat_gateway    = var.use_nat_gateway
}

# ======================== PHASE 3: SECURITY ========================
module "security_groups" {
  source = "./modules/security-groups"

  project_name          = var.project_name
  vpc_id                = module.vpc.vpc_id
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  database_subnet_cidrs = var.database_subnet_cidrs
  deploy_bastion        = var.deploy_bastion
  admin_ip              = var.admin_ip
}

module "secrets" {
  source = "./modules/secrets-manager"

  project_name = var.project_name
  db_username  = var.db_username
  db_name      = var.db_name
  db_host      = module.rds.db_host
}

# ======================== PHASE 4: COMPUTE ========================
module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  alb_sg_id         = module.security_groups.alb_sg_id
}

module "asg" {
  source = "./modules/asg"

  project_name          = var.project_name
  aws_region            = var.aws_region
  app_sg_id             = module.security_groups.app_sg_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  target_group_arn      = module.alb.target_group_arn
  instance_profile_name = module.secrets.app_instance_profile_name
  secret_name           = module.secrets.secret_name
  db_host               = module.rds.db_host
  redis_host            = module.elasticache.redis_endpoint
  docker_image          = var.docker_image
  instance_type         = var.instance_type
  desired_capacity      = var.asg_desired
  min_size              = var.asg_min
  max_size              = var.asg_max
}

# ======================== PHASE 5: DATA ========================
module "rds" {
  source = "./modules/rds"

  project_name         = var.project_name
  db_name              = var.db_name
  db_username          = module.secrets.db_username
  db_password          = module.secrets.db_password
  db_subnet_group_name = module.vpc.db_subnet_group_name
  db_sg_id             = module.security_groups.db_sg_id
  multi_az             = var.rds_multi_az
  instance_class       = var.rds_instance_class
}

module "elasticache" {
  source = "./modules/elasticache"

  project_name      = var.project_name
  subnet_group_name = module.vpc.elasticache_subnet_group_name
  redis_sg_id       = module.security_groups.redis_sg_id
}

# ======================== PHASE 7: MONITORING ========================
module "monitoring" {
  source = "./modules/monitoring"

  project_name   = var.project_name
  aws_region     = var.aws_region
  alert_email    = var.alert_email
  asg_name       = module.asg.asg_name
  db_instance_id = "${var.project_name}-db"
  alb_arn_suffix = replace(module.alb.alb_arn, "/.*:loadbalancer\\//", "")
}
