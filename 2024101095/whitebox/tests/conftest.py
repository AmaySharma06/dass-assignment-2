"""Shared fixtures for white-box tests."""
import sys
import os

# Add code directory so moneypoly package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
