"""
Unit tests for the ASG Terraform module.

Validates Auto Scaling Group configuration, launch template,
scaling policies, and required variables/outputs.
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
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the asg module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the asg module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the asg module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_launch_template_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_launch_template"' in content, \
        "aws_launch_template must be defined for ASG"


def test_autoscaling_group_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_autoscaling_group"' in content, \
        "aws_autoscaling_group must be defined"


def test_scale_out_policy_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_autoscaling_policy" "scale_out"' in content, \
        "Scale-out policy must be defined"


def test_scale_in_policy_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_autoscaling_policy" "scale_in"' in content, \
        "Scale-in policy must be defined"


def test_high_cpu_alarm_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_cloudwatch_metric_alarm" "high_cpu"' in content, \
        "High CPU CloudWatch alarm must be defined"


def test_low_cpu_alarm_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_cloudwatch_metric_alarm" "low_cpu"' in content, \
        "Low CPU CloudWatch alarm must be defined"


# ─── ASG configuration ──────────────────────────────────────────────────────

def test_health_check_type_is_elb():
    content = read(MAIN_TF)
    assert 'health_check_type         = "ELB"' in content or \
           'health_check_type = "ELB"' in content, \
        "ASG health check type must be ELB (not EC2) for ALB integration"


def test_latest_ami_data_source_used():
    content = read(MAIN_TF)
    assert 'data "aws_ami" "amazon_linux"' in content, \
        "AMI data source must be used to always get the latest Amazon Linux AMI"


def test_iam_instance_profile_attached():
    content = read(MAIN_TF)
    assert "iam_instance_profile" in content, \
        "IAM instance profile must be attached for Secrets Manager access"


def test_create_before_destroy_lifecycle():
    content = read(MAIN_TF)
    assert "create_before_destroy = true" in content, \
        "create_before_destroy lifecycle must be set to prevent downtime on updates"


# ─── Scaling thresholds ──────────────────────────────────────────────────────

def test_scale_out_cpu_threshold_70():
    content = read(MAIN_TF)
    assert "threshold           = 70" in content or "threshold = 70" in content, \
        "Scale-out threshold should be 70% CPU"


def test_scale_in_cpu_threshold_30():
    content = read(MAIN_TF)
    assert "threshold           = 30" in content or "threshold = 30" in content, \
        "Scale-in threshold should be 30% CPU"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_private_subnet_ids_variable():
    content = read(VARIABLES_TF)
    assert 'variable "private_subnet_ids"' in content


def test_target_group_arn_variable():
    content = read(VARIABLES_TF)
    assert 'variable "target_group_arn"' in content


def test_instance_type_variable():
    content = read(VARIABLES_TF)
    assert 'variable "instance_type"' in content


def test_docker_image_variable():
    content = read(VARIABLES_TF)
    assert 'variable "docker_image"' in content


def test_capacity_variables():
    content = read(VARIABLES_TF)
    assert 'variable "desired_capacity"' in content
    assert 'variable "min_size"' in content
    assert 'variable "max_size"' in content


# ─── Required outputs ───────────────────────────────────────────────────────

def test_asg_name_output():
    content = read(OUTPUTS_TF)
    assert 'output "asg_name"' in content, "asg_name output must be exposed for monitoring"
