# conftest.py — Pytest configuration for the test suite.
# Ensures the project root is on the Python path for all tests.

import sys
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))
