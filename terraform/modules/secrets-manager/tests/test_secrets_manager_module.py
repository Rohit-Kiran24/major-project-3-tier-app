"""
Unit tests for the Secrets Manager Terraform module.

Validates IAM roles, policies, Secrets Manager secret structure,
and required outputs for runtime credential injection.
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
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the secrets-manager module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the secrets-manager module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the secrets-manager module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_random_password_resource():
    content = read(MAIN_TF)
    assert 'resource "random_password"' in content, \
        "random_password must be used to generate DB password (no hardcoded credentials)"


def test_secretsmanager_secret_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_secretsmanager_secret"' in content, \
        "aws_secretsmanager_secret must be defined"


def test_secretsmanager_secret_version_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_secretsmanager_secret_version"' in content, \
        "aws_secretsmanager_secret_version must be defined to store credentials"


def test_iam_role_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_iam_role" "app_role"' in content, \
        "IAM role for EC2 instances must be defined"


def test_iam_policy_secrets_read():
    content = read(MAIN_TF)
    assert 'resource "aws_iam_policy" "secrets_read"' in content, \
        "IAM policy for reading secrets must be defined"


def test_instance_profile_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_iam_instance_profile"' in content, \
        "IAM instance profile must be defined to attach role to EC2"


# ─── IAM: Least privilege ────────────────────────────────────────────────────

def test_secrets_policy_restricts_to_get_and_describe():
    content = read(MAIN_TF)
    assert "secretsmanager:GetSecretValue" in content, \
        "IAM policy must allow GetSecretValue"
    assert "secretsmanager:DescribeSecret" in content, \
        "IAM policy must allow DescribeSecret"


def test_ec2_assume_role_principal():
    content = read(MAIN_TF)
    assert '"ec2.amazonaws.com"' in content, \
        "IAM role trust policy must allow ec2.amazonaws.com to assume the role"


# ─── Managed policies attached ───────────────────────────────────────────────

def test_ssm_policy_attached():
    content = read(MAIN_TF)
    assert "AmazonSSMManagedInstanceCore" in content, \
        "SSM policy must be attached for Session Manager (replaces bastion)"


def test_cloudwatch_policy_attached():
    content = read(MAIN_TF)
    assert "CloudWatchAgentServerPolicy" in content, \
        "CloudWatch agent policy must be attached for monitoring"


# ─── Secret stored as JSON ───────────────────────────────────────────────────

def test_secret_uses_jsonencode():
    content = read(MAIN_TF)
    assert "jsonencode" in content, \
        "Secret value must be stored as JSON (jsonencode) for structured access"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_db_username_variable():
    content = read(VARIABLES_TF)
    assert 'variable "db_username"' in content


# ─── Required outputs ───────────────────────────────────────────────────────

def test_secret_arn_output():
    content = read(OUTPUTS_TF)
    assert 'output "secret_arn"' in content, "secret_arn must be exposed as output"


def test_secret_name_output():
    content = read(OUTPUTS_TF)
    assert 'output "secret_name"' in content, "secret_name must be exposed as output"


def test_app_instance_profile_output():
    content = read(OUTPUTS_TF)
    assert 'output "app_instance_profile_name"' in content, \
        "app_instance_profile_name must be exposed for ASG module"


def test_db_password_output_is_sensitive():
    content = read(OUTPUTS_TF)
    # Check db_password output has sensitive = true
    assert "sensitive   = true" in content or "sensitive = true" in content, \
        "db_password output must be marked sensitive"
