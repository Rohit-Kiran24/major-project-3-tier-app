"""
Unit tests for the ALB Terraform module.

Validates ALB resource structure, health check configuration,
sticky sessions, and required outputs without AWS credentials.
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
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the alb module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the alb module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the alb module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_alb_resource_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_lb" "main"' in content, "aws_lb resource must be defined"


def test_target_group_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_lb_target_group"' in content, "aws_lb_target_group must be defined"


def test_http_listener_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_lb_listener" "http"' in content, \
        "HTTP listener must be defined on port 80"


# ─── ALB configuration ──────────────────────────────────────────────────────

def test_alb_is_application_type():
    content = read(MAIN_TF)
    assert 'load_balancer_type = "application"' in content, \
        "ALB must be of type 'application'"


def test_alb_is_external_facing():
    content = read(MAIN_TF)
    assert "internal           = false" in content or "internal = false" in content, \
        "ALB must be external-facing (internal = false)"


# ─── Target group health check ───────────────────────────────────────────────

def test_health_check_path_is_health_endpoint():
    content = read(MAIN_TF)
    assert 'path                = "/health"' in content or 'path = "/health"' in content, \
        "Health check path must be /health"


def test_health_check_port_5000():
    content = read(MAIN_TF)
    assert '"5000"' in content, "Health check must target port 5000 (Flask app port)"


def test_health_check_returns_200():
    content = read(MAIN_TF)
    assert 'matcher             = "200"' in content or 'matcher = "200"' in content, \
        "Health check must expect HTTP 200"


# ─── Sticky sessions for WebSocket ───────────────────────────────────────────

def test_sticky_sessions_enabled():
    content = read(MAIN_TF)
    assert "stickiness" in content, \
        "Sticky sessions must be configured for WebSocket affinity"


def test_sticky_sessions_lb_cookie_type():
    content = read(MAIN_TF)
    assert 'type            = "lb_cookie"' in content or 'type = "lb_cookie"' in content, \
        "Sticky session type must be lb_cookie"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_vpc_id_variable():
    content = read(VARIABLES_TF)
    assert 'variable "vpc_id"' in content


def test_public_subnet_ids_variable():
    content = read(VARIABLES_TF)
    assert 'variable "public_subnet_ids"' in content


def test_alb_sg_id_variable():
    content = read(VARIABLES_TF)
    assert 'variable "alb_sg_id"' in content


# ─── Required outputs ───────────────────────────────────────────────────────

def test_alb_dns_name_output():
    content = read(OUTPUTS_TF)
    assert 'output "alb_dns_name"' in content, "alb_dns_name output must be exposed"


def test_target_group_arn_output():
    content = read(OUTPUTS_TF)
    assert 'output "target_group_arn"' in content, \
        "target_group_arn output must be exposed (used by ASG)"


def test_alb_arn_output():
    content = read(OUTPUTS_TF)
    assert 'output "alb_arn"' in content, "alb_arn output must be exposed"
