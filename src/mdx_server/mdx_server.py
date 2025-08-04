#!/usr/bin/env python3
"""
MDX Dictionary Server - Modern Multi-Dictionary Implementation

A high-performance HTTP server for MDX dictionary files with multi-dictionary support.
"""

import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import unquote
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

# Handle both relative imports (when run as module) and direct execution
try:
    from .config import ServerConfig, load_config
    from .file_util import file_util_get_ext
    from .mdx_util import get_definition_mdd
    from .multi_dict_manager import MultiDictManager
except ImportError:
    # Running directly, add parent directory to path
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    from mdx_server.config import ServerConfig, load_config
    from mdx_server.file_util import file_util_get_ext
    from mdx_server.mdx_util import get_definition_mdd
    from mdx_server.multi_dict_manager import MultiDictManager


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-threaded WSGI server."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type,
        max_threads: int = 20,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.max_threads = max_threads


class SilentWSGIRequestHandler(WSGIRequestHandler):
    """WSGI request handler with reduced logging."""

    def log_message(self, format: str, *args: Any) -> None:
        pass


def make_threaded_server(
    host: str, port: int, app: Any, max_threads: int = 20
) -> ThreadedWSGIServer:
    """Create a multi-threaded WSGI server."""
    httpd = ThreadedWSGIServer((host, port), SilentWSGIRequestHandler, max_threads)
    httpd.set_app(app)
    return httpd


class MDXServer:
    """Modern Multi-Dictionary MDX Server."""

    CONTENT_TYPES: dict[str, str] = {
        "html": "text/html; charset=utf-8",
        "js": "application/javascript",
        "ico": "image/x-icon",
        "css": "text/css",
        "jpg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "wav": "audio/wav",
        "spx": "audio/ogg",
        "ogg": "audio/ogg",
        "eot": "font/opentype",
        "svg": "image/svg+xml",
        "ttf": "application/font-ttf",
        "woff": "application/font-woff",
        "woff2": "application/font-woff2",
    }

    def __init__(self, config: ServerConfig) -> None:
        """Initialize the MDX server."""
        self.config = config
        self.multi_dict_manager = MultiDictManager(config)
        self.logger = self._setup_logging()
        self._resource_index: dict[str, Any] = {}
        self._route_handlers = self._init_route_handlers()

        if not self.multi_dict_manager.builders:
            raise RuntimeError("No dictionaries loaded - server cannot start")

        self._build_resource_index()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        level = logging.DEBUG if self.config.debug else logging.INFO
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _init_route_handlers(self) -> dict[str, Callable]:
        """Initialize route handlers mapping."""
        return {
            "/health": self._handle_health_check,
            "/api/dicts": self._handle_dict_list,
            "/api/dictionaries": self._handle_dict_list,
        }

    def _build_resource_index(self) -> None:
        """Build reverse index for faster resource lookup using all available MDD resources."""
        self.logger.info("Building resource index...")
        total_resources = 0

        for dict_id, builder in self.multi_dict_manager.builders.items():
            try:
                # Get all MDD keys (resource paths) from this dictionary
                if hasattr(builder, "get_mdd_keys"):
                    mdd_keys = builder.get_mdd_keys()
                    dict_resources = 0

                    for key in mdd_keys:
                        if key:
                            # Normalize the key to a web path format
                            # Convert \html\file.js to file.js, \file.js to file.js
                            normalized_key = key.replace("\\", "/").strip("/")
                            if normalized_key.startswith("html/"):
                                normalized_key = normalized_key[
                                    5:
                                ]  # Remove 'html/' prefix

                            # Only index if we don't already have this resource from another dict
                            if normalized_key not in self._resource_index:
                                # Verify the resource actually has content
                                try:
                                    result = get_definition_mdd(key, builder)
                                    if result and result[0]:  # Has non-empty content
                                        self._resource_index[normalized_key] = dict_id
                                        dict_resources += 1
                                except Exception:
                                    continue

                    self.logger.debug(
                        f"Dictionary {dict_id}: indexed {dict_resources} resources"
                    )
                    total_resources += dict_resources
                else:
                    self.logger.warning(
                        f"Dictionary {dict_id} doesn't support get_mdd_keys()"
                    )

            except Exception as e:
                self.logger.debug(f"Error building index for {dict_id}: {e}")

        self.logger.info(
            f"Resource index built with {total_resources} entries from {len(self.multi_dict_manager.builders)} dictionaries"
        )

    def _validate_word(self, word: str) -> bool:
        """Validate word input for security."""
        if not word or len(word) > 100:
            return False

        # Check for path traversal attempts
        return not any(char in word for char in ["..", "/", "\\"])

    def _get_content_type(self, file_path: str) -> str:
        """Get content type for a file."""
        ext = file_util_get_ext(file_path)
        return self.CONTENT_TYPES.get(ext, "text/html; charset=utf-8")

    def _handle_mdd_resource(
        self, path_info: str, start_response: Any, dict_route: str = ""
    ) -> list[bytes]:
        """Handle MDD resource requests."""
        try:
            content_type = self._get_content_type(path_info)

            builder = (
                self.multi_dict_manager.get_dictionary_by_route(dict_route)
                if dict_route
                else self._find_resource_in_any_dictionary(path_info)
            )

            if builder:
                # MDD resources use '\\' as a path separator internally, regardless of OS.
                # We create a list of possible keys to try. The final normalization
                # (e.g., 'css/style.css' -> 'css\style.css') is handled by get_definition_mdd.
                search_paths = [
                    path_info,
                    f"\\{path_info}",
                    f"\\html\\{path_info}",
                ]

                for search_path in search_paths:
                    result = get_definition_mdd(search_path, builder)
                    if result and result[0]:
                        start_response("200 OK", [("Content-Type", content_type)])
                        return result

            return self._handle_not_found(start_response)

        except OSError as e:
            self.logger.error(f"MDD file access error: {e}")
            return self._handle_error(start_response, "Resource file not accessible")
        except Exception as e:
            self.logger.error(f"MDD lookup error: {e}")
            return self._handle_error(start_response, "Resource lookup failed")

    def _find_resource_in_any_dictionary(self, path_info: str):
        """Find resource in any available dictionary using index for O(1) lookup."""
        # Multiple normalization attempts for better cache hit rate
        normalized_paths = [
            path_info.lstrip("/"),  # Remove leading slashes
            path_info.lstrip("/\\"),  # Remove leading slashes and backslashes
            path_info.replace("\\", "/").lstrip("/"),  # Convert backslashes and strip
        ]

        # Remove duplicates while preserving order
        normalized_paths = list(dict.fromkeys(normalized_paths))

        # Try indexed lookup first with all normalized paths
        for normalized_path in normalized_paths:
            if normalized_path in self._resource_index:
                dict_id = self._resource_index[normalized_path]
                if dict_id in self.multi_dict_manager.builders:
                    return self.multi_dict_manager.builders[dict_id]

        # Fallback to linear search for unindexed resources
        search_paths = [
            path_info,
            os.path.join("", path_info),
            os.path.join("", "html", path_info),
        ]

        for builder in self.multi_dict_manager.builders.values():
            try:
                for search_path in search_paths:
                    result = get_definition_mdd(search_path, builder)
                    if result and result[0]:
                        # Cache the found resource for future lookups using the original path
                        dict_id = next(
                            dict_id
                            for dict_id, b in self.multi_dict_manager.builders.items()
                            if b == builder
                        )
                        # Cache all normalized paths for better hit rate
                        for norm_path in normalized_paths:
                            if norm_path not in self._resource_index:
                                self._resource_index[norm_path] = dict_id
                        return builder
            except OSError:
                continue
            except Exception:
                continue
        return None

    def _handle_word_lookup(
        self, word: str, start_response: Any, dict_route: str = ""
    ) -> list[bytes]:
        """Handle word lookup requests."""
        if not self._validate_word(word):
            return self._handle_error(start_response, "Invalid word")

        try:
            results = self.multi_dict_manager.query_dictionary(dict_route, word)
            if results:
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [result.encode("utf-8") for result in results]
            else:
                start_response(
                    "404 Not Found", [("Content-Type", "text/html; charset=utf-8")]
                )
                return [f"<h1>Word '{word}' not found in dictionary</h1>".encode()]

        except OSError as e:
            self.logger.error(f"Dictionary file access error for '{word}': {e}")
            return self._handle_error(start_response, "Dictionary file not accessible")
        except Exception as e:
            self.logger.error(f"Word lookup error for '{word}': {e}")
            return self._handle_error(start_response, "Word lookup failed")

    def _handle_not_found(self, start_response: Any) -> list[bytes]:
        """Handle 404 not found."""
        start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
        return [b"<h1>404 - Not Found</h1>"]

    def _handle_error(self, start_response: Any, message: str) -> list[bytes]:
        """Handle server errors."""
        start_response(
            "500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")]
        )
        return [f"<h1>Error: {message}</h1>".encode()]

    def _handle_health_check(self, start_response: Any) -> list[bytes]:
        """Handle health check requests."""
        if self.multi_dict_manager.builders:
            status_data = {
                "status": "healthy",
                "mode": "multi",
                "dictionaries": len(self.multi_dict_manager.builders),
            }
            start_response("200 OK", [("Content-Type", "application/json")])
            return [json.dumps(status_data).encode()]
        else:
            status_data = {"status": "unhealthy", "dictionary": "not_loaded"}
            start_response(
                "503 Service Unavailable", [("Content-Type", "application/json")]
            )
            return [json.dumps(status_data).encode()]

    def _handle_dict_list(self, start_response: Any) -> list[bytes]:
        """Handle dictionary list API requests."""
        try:
            dict_list = self.multi_dict_manager.get_dictionary_list()
            response = {
                "dictionaries": dict_list,
                "mode": "multi",
                "total": len(dict_list),
            }
            start_response("200 OK", [("Content-Type", "application/json")])
            return [json.dumps(response, ensure_ascii=False).encode("utf-8")]
        except OSError as e:
            self.logger.error(f"Dictionary file access error: {e}")
            return self._handle_error(start_response, "Dictionary files not accessible")
        except Exception as e:
            self.logger.error(f"Dictionary list error: {e}")
            return self._handle_error(start_response, "Failed to get dictionary list")

    def wsgi_application(
        self, environ: dict[str, Any], start_response: Any
    ) -> list[bytes]:
        """WSGI application handler with clean routing logic."""
        try:
            path_info = unquote(
                environ["PATH_INFO"].encode("iso8859-1").decode("utf-8")
            )
            self.logger.debug(f"Request: {path_info}")

            # Route the request using a clean dispatch system
            return self._route_request(path_info, start_response)

        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error: {e}")
            return self._handle_error(start_response, "Invalid character encoding")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            return self._handle_error(start_response, "Internal server error")

    def _route_request(self, path_info: str, start_response: Any) -> list[bytes]:
        """Clean request routing with explicit handling for different types."""
        # Direct API routes
        if path_info in self._route_handlers:
            return self._route_handlers[path_info](start_response)

        # Parse path components
        clean_path = path_info.strip("/")
        path_parts = clean_path.split("/") if clean_path else []

        # Empty path - show dictionary list
        if not path_parts:
            return self._handle_dict_list(start_response)

        # Single component paths
        if len(path_parts) == 1:
            component = path_parts[0]
            return self._handle_single_component(component, start_response)

        # Multi-component paths (dict_route/resource or dict_route/word)
        return self._handle_multi_component(path_parts, start_response)

    def _handle_single_component(
        self, component: str, start_response: Any
    ) -> list[bytes]:
        """Handle single path component (resource or word lookup)."""
        # Check if it's a resource file
        if file_util_get_ext(component) in self.CONTENT_TYPES:
            return self._handle_mdd_resource(component, start_response)

        # Otherwise it's a word lookup in default dictionary
        return self._handle_word_lookup(component, start_response, "")

    def _handle_multi_component(
        self, path_parts: list[str], start_response: Any
    ) -> list[bytes]:
        """Handle multi-component paths with dictionary routing."""
        potential_route = path_parts[0]
        remaining_path = "/".join(path_parts[1:])

        # Check if first component is a valid dictionary route
        if self.multi_dict_manager.get_dictionary_by_route(potential_route):
            # Valid dictionary route
            if file_util_get_ext(path_parts[-1]) in self.CONTENT_TYPES:
                # Resource request: /dict_route/path/to/resource.ext
                return self._handle_mdd_resource(
                    remaining_path, start_response, potential_route
                )
            else:
                # Word lookup: /dict_route/word
                return self._handle_word_lookup(
                    remaining_path, start_response, potential_route
                )

        # Not a valid dictionary route, treat whole path as resource or return not found
        full_path = "/".join(path_parts)
        if file_util_get_ext(path_parts[-1]) in self.CONTENT_TYPES:
            return self._handle_mdd_resource(full_path, start_response, "")

        # Fallback: not found
        return self._handle_not_found(start_response)

    def run(self) -> None:
        """Run the server."""
        self.logger.info(
            f"Starting server with {len(self.multi_dict_manager.builders)} dictionaries"
        )

        if self.config.use_gunicorn and self.config.server_type == "gunicorn":
            self._run_gunicorn()
        else:
            self._run_wsgi_server()

    def _run_wsgi_server(self) -> None:
        """Run with built-in WSGI server."""
        try:
            self.logger.info(
                f"Starting {self.config.server_type} server on {self.config.host}:{self.config.port}"
            )

            if self.config.server_type == "threaded":
                httpd = make_threaded_server(
                    self.config.host,
                    self.config.port,
                    self.wsgi_application,
                    max_threads=self.config.max_threads,
                )
                self.logger.info(
                    f"Multi-threaded server (max_threads={self.config.max_threads}) ready at http://localhost:{self.config.port}/"
                )
            else:
                httpd = make_server(  # type: ignore[assignment]
                    self.config.host, self.config.port, self.wsgi_application
                )
                self.logger.info(
                    f"Simple server ready at http://localhost:{self.config.port}/"
                )

            httpd.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except OSError as e:
            self.logger.error(f"Server socket error: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)

    def _run_gunicorn(self) -> None:
        """Run with Gunicorn for production."""
        try:
            self.logger.info(
                f"Starting Gunicorn server with {self.config.gunicorn_workers} workers"
            )

            # Create a gunicorn app module
            app_module = f"{__name__}:create_app()"

            cmd = [
                "gunicorn",
                "--bind",
                f"{self.config.host}:{self.config.port}",
                "--workers",
                str(self.config.gunicorn_workers),
                "--threads",
                str(self.config.gunicorn_threads),
                "--timeout",
                str(self.config.connection_timeout),
                "--access-logfile",
                "-" if self.config.debug else "/dev/null",
                "--error-logfile",
                "-",
                "--worker-class",
                "gthread",
                app_module,
            ]

            self.logger.info(f"Gunicorn command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            self.logger.error("Gunicorn not found. Install with: pip install gunicorn")
            self.logger.info("Falling back to threaded WSGI server...")
            self.config.server_type = "threaded"
            self._run_wsgi_server()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Gunicorn process error: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Gunicorn error: {e}")
            sys.exit(1)


def create_app() -> Any:
    """Create WSGI application for Gunicorn."""
    config = load_config()
    config.setup_logging()
    return MDXServer(config).wsgi_application


def main() -> None:
    """Main entry point."""
    config = load_config()
    config.setup_logging()

    try:
        server = MDXServer(config)
        server.run()
    except RuntimeError as e:
        logging.error(f"Server initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
