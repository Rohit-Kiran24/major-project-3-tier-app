"""
Unit tests for the VPC Terraform module.

Validates module structure, required variables, outputs,
and key configuration properties without requiring AWS credentials.
"""
import os
import re
import pytest


MODULE_DIR = os.path.join(os.path.dirname(__file__), "..")
MAIN_TF = os.path.join(MODULE_DIR, "main.tf")
VARIABLES_TF = os.path.join(MODULE_DIR, "variables.tf")
OUTPUTS_TF = os.path.join(MODULE_DIR, "outputs.tf")
NAT_TF = os.path.join(MODULE_DIR, "nat_instance.tf")


# ─── Helpers ────────────────────────────────────────────────────────────────

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ─── File existence ─────────────────────────────────────────────────────────

def test_main_tf_exists():
    assert os.path.isfile(MAIN_TF), "main.tf must exist in the vpc module"


def test_variables_tf_exists():
    assert os.path.isfile(VARIABLES_TF), "variables.tf must exist in the vpc module"


def test_outputs_tf_exists():
    assert os.path.isfile(OUTPUTS_TF), "outputs.tf must exist in the vpc module"


def test_nat_instance_tf_exists():
    assert os.path.isfile(NAT_TF), "nat_instance.tf must exist in the vpc module"


# ─── Required resources ─────────────────────────────────────────────────────

def test_vpc_resource_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_vpc" "main"' in content, "aws_vpc resource must be defined"


def test_internet_gateway_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_internet_gateway"' in content, "aws_internet_gateway must be defined"


def test_three_subnet_tiers_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_subnet" "public"' in content, "Public subnet must be defined"
    assert 'resource "aws_subnet" "private"' in content, "Private subnet must be defined"
    assert 'resource "aws_subnet" "database"' in content, "Database subnet must be defined"


def test_db_subnet_group_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_db_subnet_group"' in content, "aws_db_subnet_group must be defined"


def test_elasticache_subnet_group_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_elasticache_subnet_group"' in content, \
        "aws_elasticache_subnet_group must be defined"


def test_route_tables_defined():
    content = read(MAIN_TF)
    assert 'resource "aws_route_table" "public"' in content
    assert 'resource "aws_route_table" "private"' in content
    assert 'resource "aws_route_table" "database"' in content


# ─── Security: DNS enabled ───────────────────────────────────────────────────

def test_vpc_dns_support_enabled():
    content = read(MAIN_TF)
    assert "enable_dns_support   = true" in content or "enable_dns_support = true" in content, \
        "DNS support must be enabled on the VPC"


def test_vpc_dns_hostnames_enabled():
    content = read(MAIN_TF)
    assert "enable_dns_hostnames = true" in content or "enable_dns_hostnames= true" in content, \
        "DNS hostnames must be enabled on the VPC"


# ─── Required variables ─────────────────────────────────────────────────────

def test_project_name_variable_defined():
    content = read(VARIABLES_TF)
    assert 'variable "project_name"' in content


def test_vpc_cidr_variable_defined():
    content = read(VARIABLES_TF)
    assert 'variable "vpc_cidr"' in content


def test_availability_zones_variable_defined():
    content = read(VARIABLES_TF)
    assert 'variable "availability_zones"' in content


def test_use_nat_gateway_toggle_variable_defined():
    content = read(VARIABLES_TF)
    assert 'variable "use_nat_gateway"' in content, \
        "use_nat_gateway toggle variable must be defined"


# ─── Required outputs ───────────────────────────────────────────────────────

def test_vpc_id_output_defined():
    content = read(OUTPUTS_TF)
    assert 'output "vpc_id"' in content


def test_public_subnet_ids_output_defined():
    content = read(OUTPUTS_TF)
    assert 'output "public_subnet_ids"' in content


def test_private_subnet_ids_output_defined():
    content = read(OUTPUTS_TF)
    assert 'output "private_subnet_ids"' in content


def test_database_subnet_ids_output_defined():
    content = read(OUTPUTS_TF)
    assert 'output "database_subnet_ids"' in content


def test_db_subnet_group_name_output_defined():
    content = read(OUTPUTS_TF)
    assert 'output "db_subnet_group_name"' in content


# ─── NAT configuration ──────────────────────────────────────────────────────

def test_nat_instance_uses_source_dest_check_false():
    content = read(NAT_TF)
    assert "source_dest_check           = false" in content or \
           "source_dest_check = false" in content, \
        "NAT instance must have source_dest_check = false for NAT to work"


def test_nat_gateway_conditional():
    content = read(MAIN_TF)
    assert "var.use_nat_gateway" in content, \
        "NAT gateway should be conditionally deployed via use_nat_gateway variable"
