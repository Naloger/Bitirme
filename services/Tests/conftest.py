# -*- coding: utf-8 -*-
"""Pytest configuration for tests."""
import sys
from pathlib import Path

# Add services directory to sys.path so pytest can find modules
services_dir = Path(__file__).parent.parent
sys.path.insert(0, str(services_dir))
