#!/usr/bin/env python3
"""
Multi-Dictionary Manager for MDX Server.
"""

import logging
from pathlib import Path

from .config import DictConfig, ServerConfig
from .mdict_query import IndexBuilder


class MultiDictManager:
    """Multi-dictionary manager for handling multiple MDX dictionaries."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.builders: dict[str, IndexBuilder] = {}
        self.dict_configs: dict[str, DictConfig] = config.dictionaries.copy()

        # Auto-discover dictionaries
        config.auto_discover_dictionaries()
        self.dict_configs.update(config.dictionaries)

        # Load dictionaries
        self.load_dictionaries()

    def load_dictionaries(self) -> None:
        """Load all enabled dictionaries."""
        for dict_id, dict_config in self.dict_configs.items():
            if not dict_config.enabled:
                continue

            # Handle relative and absolute paths
            dict_path = Path(dict_config.path)
            if not dict_path.is_absolute():
                dict_path = Path.cwd() / dict_path

            if not dict_path.exists():
                logging.warning(f"Dictionary file not found: {dict_path}")
                continue

            try:
                builder = IndexBuilder(dict_path)
                self.builders[dict_id] = builder
                logging.info(f"Loaded dictionary: {dict_id} ({dict_config.name})")
            except Exception as e:
                logging.error(f"Failed to load dictionary {dict_id}: {e}")

    def get_dictionary_by_route(self, route: str) -> IndexBuilder | None:
        """Get dictionary by route."""
        # Default route (empty string)
        if not route:
            # Find default dictionary or first available dictionary
            if "default" in self.builders:
                return self.builders["default"]
            elif self.builders:
                return next(iter(self.builders.values()))
            return None

        # Find dictionary matching the route
        for dict_id, dict_config in self.dict_configs.items():
            if dict_config.route == route and dict_id in self.builders:
                return self.builders[dict_id]

        return None

    def get_dictionary_by_id(self, dict_id: str) -> IndexBuilder | None:
        """Get dictionary by ID."""
        return self.builders.get(dict_id)

    def query_dictionary(self, dict_id_or_route: str, word: str) -> list[str]:
        """Query specified dictionary."""
        # Try as route first
        builder = self.get_dictionary_by_route(dict_id_or_route)

        # If not found, try as ID
        if not builder:
            builder = self.get_dictionary_by_id(dict_id_or_route)

        if not builder:
            return []

        try:
            return builder.mdx_lookup(word)
        except Exception as e:
            logging.error(f"Query error for {word} in {dict_id_or_route}: {e}")
            return []

    def get_dictionary_list(self) -> list[dict]:
        """Get dictionary list."""
        result = []
        for dict_id, dict_config in self.dict_configs.items():
            status = "loaded" if dict_id in self.builders else "error"
            result.append(
                {
                    "id": dict_id,
                    "name": dict_config.name,
                    "route": dict_config.route,
                    "path": dict_config.path,
                    "enabled": dict_config.enabled,
                    "status": status,
                }
            )
        return result

    def get_available_routes(self) -> list[str]:
        """Get available routes list."""
        routes = []
        for dict_id, dict_config in self.dict_configs.items():
            if dict_id in self.builders and dict_config.route:
                routes.append(dict_config.route)
        return routes
