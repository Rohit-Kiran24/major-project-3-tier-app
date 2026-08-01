"""
Unit tests for the ElastiCache Terraform module.

Validates Redis cluster configuration for WebSocket pub/sub,
required variables, and outputs without AWS credentials.
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
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the elasticache module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the elasticache module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the elasticache module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_elasticache_cluster_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_elasticache_cluster" "redis"' in content, \
        "aws_elasticache_cluster must be defined"


# ─── Redis configuration ─────────────────────────────────────────────────────

def test_redis_engine():
    content = read(MAIN_TF)
    assert 'engine               = "redis"' in content or \
           'engine = "redis"' in content, \
        "Engine must be redis"


def test_redis_version_7():
    content = read(MAIN_TF)
    assert '"7.0"' in content or '"7"' in content, \
        "Redis version must be 7.x for latest features"


def test_redis_port_6379():
    content = read(MAIN_TF)
    assert "port                 = 6379" in content or \
           "port = 6379" in content, \
        "Redis must listen on port 6379"


def test_subnet_group_configured():
    content = read(MAIN_TF)
    assert "subnet_group_name" in content, \
        "Redis must be placed in the correct subnet group (private subnets)"


def test_security_group_configured():
    content = read(MAIN_TF)
    assert "security_group_ids" in content, \
        "Redis must have security groups configured"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_subnet_group_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "subnet_group_name"' in content, \
        "subnet_group_name variable must be defined for VPC placement"


def test_redis_sg_id_variable():
    content = read(VARIABLES_TF)
    assert 'variable "redis_sg_id"' in content, \
        "redis_sg_id variable must be defined"


def test_node_type_variable():
    content = read(VARIABLES_TF)
    assert 'variable "node_type"' in content, \
        "node_type variable must be defined for cost flexibility"


# ─── Required outputs ───────────────────────────────────────────────────────

def test_redis_endpoint_output():
    content = read(OUTPUTS_TF)
    assert 'output "redis_endpoint"' in content, \
        "redis_endpoint output must be exposed for Flask app configuration"


def test_redis_port_output():
    content = read(OUTPUTS_TF)
    assert 'output "redis_port"' in content, \
        "redis_port output must be exposed"
