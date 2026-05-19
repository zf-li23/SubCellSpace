#!/usr/bin/env python3
"""SubCellSpace CLI wrapper for cluster — no pip install needed."""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

from src.cli import main
main()
