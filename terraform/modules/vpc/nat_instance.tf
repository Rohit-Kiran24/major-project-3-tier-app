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
  count                       = var.use_nat_gateway ? 0 : 1
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.public[0].id
  associate_public_ip_address = true
  source_dest_check           = false # CRITICAL for NAT functionality
  vpc_security_group_ids      = [aws_security_group.nat[0].id]

  user_data = <<-EOF
    #!/bin/bash
    # Enable IP forwarding for NAT
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

    # Configure iptables for NAT masquerading
    yum install -y iptables-services
    iptables -t nat -A POSTROUTING -o enX0 -j MASQUERADE
    iptables -A FORWARD -i enX0 -o enX0 -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i enX0 -o enX0 -j ACCEPT
    service iptables save
    systemctl enable iptables
  EOF

  tags = {
    Name = "${var.project_name}-nat-instance"
  }
}
