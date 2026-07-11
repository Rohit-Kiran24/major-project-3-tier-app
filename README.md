# Three-Tier AWS Web Application — Production-Grade Chat App

[![CI](https://github.com/Rohit-Kiran24/major-project-3-tier-app/actions/workflows/ci.yml/badge.svg)](https://github.com/Rohit-Kiran24/major-project-3-tier-app/actions/workflows/ci.yml)
![Terraform](https://img.shields.io/badge/terraform-%3E%3D1.5-623CE4)
![AWS](https://img.shields.io/badge/aws-ap--south--1-FF9900)
![Python](https://img.shields.io/badge/python-3.11-3776AB)
![Flask](https://img.shields.io/badge/flask-3.0-lightgrey)
![Docker](https://img.shields.io/badge/docker-multi--stage-2496ED)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

---

## 📋 Abstract

Architecture and Automation of a Production-Grade Three-Tier Web Application on AWS Using Terraform and DevSecOps. This project addresses the limitations of monolithic and two-tier architectures by implementing a fully segmented, multi-AZ, zero-trust network architecture provisioned entirely through Infrastructure as Code.

**Evolution from**: [2-Tier Mini Project (EKS)](https://github.com/Rohit-Kiran24/mini-project-2-tier-app)

---

## 🏗️ Architecture

```
                         ┌──────────────────┐
                         │    Internet       │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │            PUBLIC SUBNETS              │
              │  ┌──────────────────────────────────┐  │
              │  │   Application Load Balancer (ALB) │  │
              │  │   HTTP:80 → Target Group :5000    │  │
              │  │   Sticky Sessions (WebSocket)     │  │
              │  └──────────────┬───────────────────┘  │
              │                 │  NAT Instance         │
              └─────────────────┼───────────────────────┘
                                │ (SG: ALB → App only)
              ┌─────────────────┼───────────────────────┐
              │           PRIVATE SUBNETS               │
              │  ┌──────────────┴───────────────────┐   │
              │  │   Auto Scaling Group (ASG)        │   │
              │  │   EC2 t2.micro × 1-3 instances    │   │
              │  │   Flask + SocketIO + Docker       │   │
              │  └──────┬──────────────┬────────────┘   │
              │         │              │                 │
              │  ┌──────┴─────┐  ┌─────┴──────────┐     │
              │  │  Redis     │  │  CloudWatch     │     │
              │  │  (pub/sub) │  │  Agent          │     │
              │  └────────────┘  └────────────────┘     │
              └─────────┬───────────────────────────────┘
                        │ (SG: App → DB only)
              ┌─────────┼───────────────────────────────┐
              │      ISOLATED SUBNETS (NO INTERNET)     │
              │  ┌──────┴───────────────────────────┐   │
              │  │   RDS PostgreSQL 15               │   │
              │  │   Multi-AZ (toggleable)           │   │
              │  │   Encrypted, zero public access   │   │
              │  └──────────────────────────────────┘   │
              └─────────────────────────────────────────┘
```

---

## ✨ Features

| Category | Feature | Detail |
|----------|---------|--------|
| **Infrastructure** | 3-Tier VPC | Public → Private → Isolated subnets, 2 AZs |
| | Zero-Trust SGs | SG-to-SG references, no CIDR-based rules |
| | NAT Instance | Cost-optimized (toggleable to NAT Gateway) |
| | Multi-AZ RDS | Toggleable for cost optimization |
| **Application** | Real-time Chat | Flask-SocketIO with WebSocket |
| | Multi-room | Create/join rooms, persistent history |
| | Authentication | Flask-Login + Bcrypt password hashing |
| | Cross-instance sync | Redis pub/sub via ElastiCache |
| **Security** | Secrets Manager | Runtime credential injection via IAM |
| | SSM Session Manager | Replaces bastion host (zero SSH exposure) |
| | Container scanning | Trivy on every build |
| | IaC scanning | Checkov for Terraform compliance |
| **DevOps** | CI Pipeline | fmt → validate → Checkov → pytest → Trivy |
| | CD Pipeline | Manual trigger: plan → apply → destroy |
| | Auto Scaling | CPU-based scale out/in policies |
| **Monitoring** | CloudWatch Alarms | CPU, storage, connections, 5XX, latency |
| | SNS Notifications | Email alerts on threshold breaches |
| | Dashboard | Single pane of glass for all 3 tiers |

---

## 📁 Project Structure

```
three-tier-aws-project/
├── terraform/                      # Infrastructure as Code
│   ├── modules/
│   │   ├── vpc/                    # VPC, subnets, IGW, NAT, route tables
│   │   ├── security-groups/        # Zero-trust SG chain
│   │   ├── alb/                    # Application Load Balancer
│   │   ├── asg/                    # Auto Scaling Group + Launch Template
│   │   ├── rds/                    # PostgreSQL Multi-AZ
│   │   ├── elasticache/            # Redis for WebSocket pub/sub
│   │   ├── secrets-manager/        # DB credentials + IAM
│   │   └── monitoring/             # CloudWatch + SNS
│   ├── main.tf                     # Root module composition
│   ├── variables.tf                # Configurable parameters
│   ├── outputs.tf                  # ALB URL, endpoints
│   ├── backend.tf                  # S3 remote state
│   └── terraform.tfvars.example
├── app/                            # Flask Chat Application
│   ├── app.py                      # Main entrypoint
│   ├── config.py                   # Secrets Manager integration
│   ├── models.py                   # SQLAlchemy models
│   ├── auth.py                     # Authentication routes
│   ├── chat.py                     # WebSocket handlers + API
│   ├── templates/                  # Jinja2 HTML templates
│   ├── static/                     # CSS + JavaScript
│   └── tests/                      # pytest unit tests
├── docker/
│   ├── Dockerfile                  # Multi-stage production build
│   └── docker-compose.yml          # Local dev (Flask + PostgreSQL + Redis)
├── scripts/
│   ├── user_data.sh.tpl            # EC2 bootstrap (Terraform template)
│   └── init_db.sql                 # Database schema
├── .github/workflows/
│   ├── ci.yml                      # PR checks pipeline
│   └── deploy.yml                  # AWS deployment pipeline
└── README.md
```

---

## 🚀 Quick Start (Local Development)

```bash
# Clone
git clone https://github.com/Rohit-Kiran24/major-project-3-tier-app.git
cd major-project-3-tier-app

# Start all services (Flask + PostgreSQL + Redis)
cd docker
docker-compose up --build

# Open http://localhost:5000
```

---

## ☁️ AWS Deployment

### Prerequisites
- AWS CLI configured (`aws configure`)
- Terraform >= 1.5 installed
- S3 bucket + DynamoDB table for state (one-time setup)

### Deploy
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

### Destroy (IMPORTANT: stop billing)
```bash
terraform destroy
```

---

## 🛡️ Security Architecture

| Layer | Protection |
|-------|-----------|
| Network | 3 subnet tiers, isolated DB (zero internet) |
| Firewall | SG-to-SG chaining (zero-trust) |
| Credentials | AWS Secrets Manager (not env vars) |
| Access | SSM Session Manager (no SSH keys) |
| IAM | Least privilege, specific resource ARNs |
| Container | Trivy vulnerability scanning |
| IaC | Checkov compliance scanning |
| Storage | RDS encryption at rest |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| IaC | Terraform 1.5+, HCL |
| Cloud | AWS (VPC, ALB, EC2, ASG, RDS, ElastiCache, Secrets Manager, CloudWatch, SNS) |
| Backend | Python 3.11, Flask 3.0, Flask-SocketIO |
| Database | PostgreSQL 15 (RDS) |
| Cache | Redis 7 (ElastiCache) |
| Server | Gunicorn + Eventlet |
| Container | Docker (multi-stage), Docker Compose |
| CI/CD | GitHub Actions |
| Security | Checkov, Trivy, flask-bcrypt |
| Monitoring | CloudWatch Alarms, SNS, CloudWatch Dashboard |

---

## 👨‍💻 Author

**Rohit Kiran** — [GitHub](https://github.com/Rohit-Kiran24)
