"""
pytest configuration — ensures the app/ directory is on the Python path
so that 'from app import create_app' and 'from models import db' work correctly
regardless of what directory pytest is invoked from.
"""
import sys
import os

# Add the app/ directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
