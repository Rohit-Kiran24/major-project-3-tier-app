"""
Unit tests for the RDS Terraform module.

Validates PostgreSQL database configuration, security settings
(encryption, no public access), and required variables/outputs.
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
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the rds module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the rds module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the rds module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_db_instance_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_db_instance" "main"' in content, \
        "aws_db_instance must be defined"


def test_db_parameter_group_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_db_parameter_group"' in content, \
        "aws_db_parameter_group must be defined for custom logging parameters"


# ─── Security: critical RDS settings ────────────────────────────────────────

def test_storage_encrypted():
    content = read(MAIN_TF)
    assert "storage_encrypted     = true" in content or \
           "storage_encrypted = true" in content, \
        "RDS storage must be encrypted at rest (storage_encrypted = true)"


def test_no_public_access():
    content = read(MAIN_TF)
    assert "publicly_accessible    = false" in content or \
           "publicly_accessible = false" in content, \
        "RDS must NOT be publicly accessible (publicly_accessible = false)"


def test_postgresql_engine():
    content = read(MAIN_TF)
    assert 'engine         = "postgres"' in content or \
           'engine = "postgres"' in content, \
        "Engine must be postgres"


def test_postgres_version_15():
    content = read(MAIN_TF)
    assert 'engine_version = "15"' in content or \
           'engine_version= "15"' in content, \
        "PostgreSQL version must be 15"


def test_backup_retention_configured():
    content = read(MAIN_TF)
    assert "backup_retention_period" in content, \
        "Backup retention period must be configured for RDS"


# ─── Sensitive variable ──────────────────────────────────────────────────────

def test_db_password_is_sensitive():
    content = read(VARIABLES_TF)
    # The password variable block should contain sensitive = true
    assert "sensitive = true" in content, \
        "db_password variable must be marked sensitive = true"


# ─── Multi-AZ toggle ─────────────────────────────────────────────────────────

def test_multi_az_variable_defined():
    content = read(VARIABLES_TF)
    assert 'variable "multi_az"' in content, \
        "multi_az variable must be defined for production/dev toggle"


def test_multi_az_used_in_resource():
    content = read(MAIN_TF)
    assert "multi_az" in content, \
        "multi_az must be referenced in the db_instance resource"


# ─── Storage type ────────────────────────────────────────────────────────────

def test_gp3_storage_type():
    content = read(MAIN_TF)
    assert '"gp3"' in content, "Storage type should be gp3 for performance/cost"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_db_subnet_group_name_variable():
    content = read(VARIABLES_TF)
    assert 'variable "db_subnet_group_name"' in content


def test_db_sg_id_variable():
    content = read(VARIABLES_TF)
    assert 'variable "db_sg_id"' in content


# ─── Required outputs ───────────────────────────────────────────────────────

def test_db_host_output():
    content = read(OUTPUTS_TF)
    assert 'output "db_host"' in content, "db_host output must be exposed"


def test_db_endpoint_output():
    content = read(OUTPUTS_TF)
    assert 'output "db_endpoint"' in content, "db_endpoint output must be exposed"
