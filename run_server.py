#!/usr/bin/env python3
"""
MDX Server Entry Point

Simple entry point for running the MDX dictionary server.
"""

from mdx_server.mdx_server import main as _main


def main():
    """Entry point for mdx-server command."""
    _main()


if __name__ == "__main__":
    main()
