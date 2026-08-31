###############################################################################
# VPC MODULE — Custom VPC with 3 subnet tiers across 2 Availability Zones
#
# Tier 1 (Public)   — ALB, NAT Instance, Bastion
# Tier 2 (Private)  — EC2 App instances (ASG), ElastiCache Redis
# Tier 3 (Isolated) — RDS Database (zero internet access)
###############################################################################

# ---------- VPC ----------
resource "aws_vpc" "main" {
  #checkov:skip=CKV2_AWS_11:VPC flow logging adds CloudWatch cost — deferred to Stage-II
  #checkov:skip=CKV2_AWS_12:Default SG restricted via aws_default_security_group resource below
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Restrict the VPC default security group — no ingress or egress allowed
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
  # No ingress or egress rules = all traffic blocked on the default SG

  tags = {
    Name = "${var.project_name}-default-sg-restricted"
  }
}

# ---------- Internet Gateway ----------
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# ---------- Public Subnets (Presentation Tier) ----------
resource "aws_subnet" "public" {
  #checkov:skip=CKV_AWS_130:Public subnets intentionally assign public IPs — required for ALB and NAT instance
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  }
}

# ---------- Private Subnets (Application Tier) ----------
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-private-${var.availability_zones[count.index]}"
    Tier = "private"
  }
}

# ---------- Isolated/Database Subnets (Data Tier) ----------
resource "aws_subnet" "database" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.database_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-database-${var.availability_zones[count.index]}"
    Tier = "isolated"
  }
}

# ---------- DB Subnet Group ----------
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# ---------- ElastiCache Subnet Group ----------
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# ---------- Elastic IP for NAT Gateway ----------
# Only allocated when the managed NAT Gateway is in use. The NAT *instance*
# path uses associate_public_ip_address instead, so allocating this
# unconditionally would leave an unattached EIP — which AWS bills for.
resource "aws_eip" "nat" {
  count  = var.use_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }

  depends_on = [aws_internet_gateway.main]
}

# ---------- Route Tables ----------

# Public Route Table — routes to Internet Gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Private Route Table — routes to NAT (instance or gateway)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# Private route — added separately so it can reference NAT instance or gateway
resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = var.use_nat_gateway ? null : aws_instance.nat[0].primary_network_interface_id
  nat_gateway_id         = var.use_nat_gateway ? aws_nat_gateway.main[0].id : null
}

# Isolated Route Table — NO default route (zero internet access)
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.main.id

  # INTENTIONALLY NO ROUTES — this is the security argument
  # The database tier has zero path to the internet

  tags = {
    Name = "${var.project_name}-database-rt"
  }
}

# ---------- Route Table Associations ----------

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "database" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

# ---------- NAT Gateway (production option, expensive) ----------
resource "aws_nat_gateway" "main" {
  count         = var.use_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-nat-gw"
  }

  depends_on = [aws_internet_gateway.main]
}
