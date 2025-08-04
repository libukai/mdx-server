#!/usr/bin/env python3
"""
MDX Server - Modern Dictionary Server for MDX Files.

A high-performance, modern HTTP server for serving MDX dictionary files
with proper error handling, type safety, and Python 3.13+ features.
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Libukai"
__email__ = "xiaobuyao@gmail.com"

# Public API exports
from .config import ServerConfig, load_config
from .mdict_query import IndexBuilder
from .mdx_server import MDXServer, create_app, main
from .mdx_util import get_definition_mdd, get_definition_mdx

__all__ = [
    "ServerConfig",
    "load_config",
    "MDXServer",
    "create_app",
    "main",
    "get_definition_mdx",
    "get_definition_mdd",
    "IndexBuilder",
    "__version__",
]
