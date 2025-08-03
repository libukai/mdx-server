#!/usr/bin/env python3
"""
MDX Server Entry Point

This script provides a clean entry point for running the MDX server,
resolving relative import issues when running the server directly.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mdx_server.mdx_server import main  # noqa: E402

if __name__ == "__main__":
    main()
