#!/usr/bin/env python3
"""Development run script for Gothog Music Player."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == '__main__':
    sys.exit(main())
