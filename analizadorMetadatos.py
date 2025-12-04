#!/usr/bin/env python3
import sys
import os

# Add the src directory to the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.main import main

if __name__ == "__main__":
    main()
