"""
Unit tests for the Security Groups Terraform module.

Validates zero-trust SG chain structure, required variables,
and key security properties without requiring AWS credentials.
"""
import os
import pytest


MODULE_DIR = os.path.join(os.path.dirname(__file__), "..")
MAIN_TF = os.path.join(MODULE_DIR, "main.tf")
VARIABLES_TF = os.path.join(MODULE_DIR, "variables.tf")
OUTPUTS_TF = os.path.join(MODULE_DIR, "outputs.tf")


# ─── Helpers ────────────────────────────────────────────────────────────────

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ─── File existence ─────────────────────────────────────────────────────────

def test_main_tf_exists():
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the security-groups module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the security-groups module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the security-groups module"


# ─── Required security groups ───────────────────────────────────────────────

def test_alb_sg_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_security_group" "alb"' in content, "ALB SG must be defined"


def test_app_sg_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_security_group" "app"' in content, "App SG must be defined"


def test_db_sg_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_security_group" "db"' in content, "DB SG must be defined"


def test_redis_sg_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_security_group" "redis"' in content, "Redis SG must be defined"


# ─── Zero-trust chain: SG-to-SG references ──────────────────────────────────

def test_app_sg_ingress_references_alb_sg():
    """App tier must only accept traffic from the ALB SG, not open CIDRs."""
    content = read(MAIN_TF)
    assert "security_groups = [aws_security_group.alb.id]" in content, \
        "App SG ingress must reference ALB SG (zero-trust), not open CIDRs"


def test_db_sg_ingress_references_app_sg():
    """DB tier must only accept traffic from the App SG, not open CIDRs."""
    content = read(MAIN_TF)
    assert "security_groups = [aws_security_group.app.id]" in content, \
        "DB/Redis SG ingress must reference App SG (zero-trust), not open CIDRs"


# ─── ALB listens on HTTP/HTTPS ───────────────────────────────────────────────

def test_alb_sg_allows_http_80():
    content = read(MAIN_TF)
    assert "from_port   = 80" in content or "from_port = 80" in content, \
        "ALB SG must allow HTTP port 80"


def test_alb_sg_allows_https_443():
    content = read(MAIN_TF)
    assert "from_port   = 443" in content or "from_port = 443" in content, \
        "ALB SG must allow HTTPS port 443"


# ─── App port 5000 ───────────────────────────────────────────────────────────

def test_app_sg_port_5000_used():
    content = read(MAIN_TF)
    assert "5000" in content, "Flask app port 5000 must appear in security group rules"


# ─── DB port 5432 ────────────────────────────────────────────────────────────

def test_db_sg_port_5432_used():
    content = read(MAIN_TF)
    assert "5432" in content, "PostgreSQL port 5432 must appear in DB security group rules"


# ─── Redis port 6379 ─────────────────────────────────────────────────────────

def test_redis_sg_port_6379_used():
    content = read(MAIN_TF)
    assert "6379" in content, "Redis port 6379 must appear in Redis security group rules"


# ─── Required variables ─────────────────────────────────────────────────────

def test_vpc_id_variable():
    content = read(VARIABLES_TF)
    assert 'variable "vpc_id"' in content


def test_vpc_cidr_variable():
    content = read(VARIABLES_TF)
    assert 'variable "vpc_cidr"' in content


def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


# ─── Required outputs ───────────────────────────────────────────────────────

def test_alb_sg_id_output():
    content = read(OUTPUTS_TF)
    assert 'output "alb_sg_id"' in content, "alb_sg_id output must be exposed"


def test_app_sg_id_output():
    content = read(OUTPUTS_TF)
    assert 'output "app_sg_id"' in content, "app_sg_id output must be exposed"


def test_db_sg_id_output():
    content = read(OUTPUTS_TF)
    assert 'output "db_sg_id"' in content, "db_sg_id output must be exposed"


def test_redis_sg_id_output():
    content = read(OUTPUTS_TF)
    assert 'output "redis_sg_id"' in content, "redis_sg_id output must be exposed"
