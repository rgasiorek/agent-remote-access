"""Pytest configuration and shared fixtures"""
import pytest
import sys
from pathlib import Path

# Add agent-api and portal-ui to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-api"))
sys.path.insert(0, str(Path(__file__).parent.parent / "portal-ui"))
