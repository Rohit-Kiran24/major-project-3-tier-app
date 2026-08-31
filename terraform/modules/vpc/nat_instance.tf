###############################################################################
# NAT INSTANCE — Cost-effective alternative to NAT Gateway
# 
# NAT Gateway costs ~$33/month. This t2.micro NAT instance costs ~$8.5/month.
# Same functionality: allows private subnet instances to reach the internet
# (for Docker image pulls, yum updates) without exposing them publicly.
#
# Toggle: set var.use_nat_gateway = true for production NAT Gateway
###############################################################################

# Find the latest Amazon Linux 2023 AMI for NAT instance
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# NAT Instance Security Group
resource "aws_security_group" "nat" {
  #checkov:skip=CKV_AWS_382:NAT instance must allow unrestricted egress to forward private subnet traffic to the internet
  #checkov:skip=CKV2_AWS_5:SG is attached to NAT instance below — Checkov cannot trace intra-module conditional references
  count       = var.use_nat_gateway ? 0 : 1
  name        = "${var.project_name}-nat-sg"
  description = "Security group for NAT instance"
  vpc_id      = aws_vpc.main.id

  # Allow all traffic from private subnets (NAT forwarding)
  ingress {
    description = "All traffic from private subnets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.private_subnet_cidrs
  }

  # Allow all outbound (internet access)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-nat-sg"
  }
}

# NAT Instance
resource "aws_instance" "nat" {
  #checkov:skip=CKV_AWS_88:NAT instance requires a public IP to route private subnet traffic to the internet
  #checkov:skip=CKV_AWS_126:Detailed monitoring adds cost — basic monitoring sufficient for NAT forwarding
  #checkov:skip=CKV_AWS_135:t2.micro does not support EBS optimization
  #checkov:skip=CKV2_AWS_41:NAT instance performs IP forwarding only — no AWS API access needed
  count                       = var.use_nat_gateway ? 0 : 1
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.public[0].id
  associate_public_ip_address = true
  source_dest_check           = false # CRITICAL for NAT functionality
  vpc_security_group_ids      = [aws_security_group.nat[0].id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Enforce IMDSv2
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted = true
  }

  # Bootstrap lives in scripts/ so it stays testable and avoids nested heredocs.
  # Path: modules/vpc/ → up 3 levels → repo root → scripts/
  user_data = file("${path.module}/../../../scripts/nat_instance.sh")

  # user_data changes must rebuild the NAT box, otherwise the route keeps
  # pointing at an instance that never applied the masquerade rule.
  user_data_replace_on_change = true

  tags = {
    Name = "${var.project_name}-nat-instance"
  }
}
