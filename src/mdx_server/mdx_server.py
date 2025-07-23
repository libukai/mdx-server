#!/usr/bin/env python3
"""
MDX Dictionary Server - Refactored Version

A modern, well-structured HTTP server for MDX dictionary files.
"""

import os
import re
import sys
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from wsgiref.simple_server import make_server
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from file_util import file_util_get_files, file_util_get_ext, file_util_read_byte, file_util_read_text, file_util_is_ext
from mdx_util import get_definition_mdx, get_definition_mdd
from mdict_query import IndexBuilder
from config import ServerConfig, load_config


def make_threaded_server(host, port, app, max_threads=20, request_queue_size=50):
    """Create a multi-threaded WSGI server."""
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
    
    class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
        allow_reuse_address = True
        daemon_threads = True
        
        def __init__(self, server_address, RequestHandlerClass):
            super().__init__(server_address, RequestHandlerClass)
            self.max_threads = max_threads
            self.request_queue_size = request_queue_size
    
    class ThreadedWSGIRequestHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            # Reduce logging noise in production
            pass
    
    httpd = ThreadedWSGIServer((host, port), ThreadedWSGIRequestHandler)
    httpd.set_app(app)
    return httpd


class MDXServer:
    """Modern MDX Dictionary Server with proper architecture."""
    
    # MIME type mappings
    CONTENT_TYPES = {
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
    
    def __init__(self, config: ServerConfig):
        """Initialize the MDX server."""
        self.config = config
        self.base_path = Path(__file__).parent
        self.dict_path = self.base_path / config.dict_directory
        self.resource_path = self.base_path / config.resource_directory
        
        self._builder: Optional[IndexBuilder] = None
        self._url_map_cache: Optional[Dict[str, str]] = None
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.config.debug else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _find_mdx_file(self) -> Optional[Path]:
        """Find the first MDX file in the dictionary directory."""
        if not self.dict_path.exists():
            self.logger.error(f"Dictionary directory not found: {self.dict_path}")
            return None
            
        for file_path in self.dict_path.glob("*.mdx"):
            return file_path
            
        self.logger.error("No MDX files found in dictionary directory")
        return None
        
    def _initialize_builder(self) -> bool:
        """Initialize the dictionary builder."""
        mdx_file = self._find_mdx_file()
        if not mdx_file:
            return False
            
        try:
            self.logger.info(f"Loading MDX file: {mdx_file}")
            self._builder = IndexBuilder(str(mdx_file))
            self.logger.info("Dictionary loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load MDX file: {e}")
            return False
            
    def _get_url_map(self) -> Dict[str, str]:
        """Get URL mapping for static resources with caching."""
        if self._url_map_cache is not None:
            return self._url_map_cache
            
        url_map = {}
        files = []
        
        if self.resource_path.exists():
            file_util_get_files(str(self.resource_path), files)
            
            for file_path in files:
                ext = file_util_get_ext(file_path)
                if ext in self.CONTENT_TYPES:
                    # Normalize path separators
                    normalized_path = file_path.replace("\\", "/")
                    match = re.search(r"/mdx(/.*)", normalized_path)
                    if match:
                        url_map[match.group(1)] = file_path
                        
        self._url_map_cache = url_map
        return url_map
        
    def _validate_word(self, word: str) -> bool:
        """Validate word input for security."""
        if not word:
            return False
            
        # Basic validation - adjust as needed
        if len(word) > 100:  # Reasonable word length limit
            return False
            
        # Check for path traversal attempts
        if ".." in word or "/" in word or "\\" in word:
            return False
            
        return True
        
    def _get_content_type(self, file_path: str) -> str:
        """Get content type for a file."""
        ext = file_util_get_ext(file_path)
        return self.CONTENT_TYPES.get(ext, "text/html; charset=utf-8")
        
    def _handle_static_resource(self, path_info: str, start_response) -> List[bytes]:
        """Handle static resource requests."""
        url_map = self._get_url_map()
        
        if path_info in url_map:
            file_path = url_map[path_info]
            content_type = self._get_content_type(file_path)
            start_response("200 OK", [("Content-Type", content_type)])
            return [file_util_read_byte(file_path)]
            
        return self._handle_not_found(start_response)
        
    def _handle_mdd_resource(self, path_info: str, start_response) -> List[bytes]:
        """Handle MDD resource requests."""
        if not self._builder:
            return self._handle_error(start_response, "Dictionary not loaded")
            
        try:
            content_type = self._get_content_type(path_info)
            start_response("200 OK", [("Content-Type", content_type)])
            return get_definition_mdd(path_info, self._builder)
        except Exception as e:
            self.logger.error(f"MDD lookup error: {e}")
            return self._handle_error(start_response, "Resource lookup failed")
            
    def _handle_word_lookup(self, word: str, start_response) -> List[bytes]:
        """Handle word lookup requests."""
        if not self._builder:
            return self._handle_error(start_response, "Dictionary not loaded")
            
        if not self._validate_word(word):
            return self._handle_error(start_response, "Invalid word")
            
        try:
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return get_definition_mdx(word, self._builder)
        except Exception as e:
            self.logger.error(f"Word lookup error for '{word}': {e}")
            return self._handle_error(start_response, "Word lookup failed")
            
    def _handle_not_found(self, start_response) -> List[bytes]:
        """Handle 404 not found."""
        start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
        return [b"<h1>404 - Not Found</h1>"]
        
    def _handle_error(self, start_response, message: str) -> List[bytes]:
        """Handle server errors."""
        start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
        return [f"<h1>Error: {message}</h1>".encode('utf-8')]
        
    def _handle_health_check(self, start_response) -> List[bytes]:
        """Handle health check requests."""
        if self._builder:
            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"status": "healthy", "dictionary": "loaded"}']
        else:
            start_response("503 Service Unavailable", [("Content-Type", "application/json")])
            return [b'{"status": "unhealthy", "dictionary": "not_loaded"}']
        
    def wsgi_application(self, environ: Dict[str, Any], start_response) -> List[bytes]:
        """WSGI application handler."""
        try:
            path_info = environ["PATH_INFO"].encode("iso8859-1").decode("utf-8")
            self.logger.debug(f"Request: {path_info}")
            
            # Extract word from path
            match = re.match(r"/(.*)", path_info)
            word = match.group(1) if match else ""
            
            url_map = self._get_url_map()
            
            # Handle static resources
            if path_info in url_map:
                return self._handle_static_resource(path_info, start_response)
                
            # Handle MDD resources
            elif file_util_get_ext(path_info) in self.CONTENT_TYPES:
                return self._handle_mdd_resource(path_info, start_response)
                
            # Handle health check
            elif path_info == "/health":
                return self._handle_health_check(start_response)
                
            # Handle word lookup
            else:
                return self._handle_word_lookup(word, start_response)
                
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            return self._handle_error(start_response, "Internal server error")
            
    def run(self) -> None:
        """Run the server."""
        if not self._initialize_builder():
            self.logger.error("Failed to initialize dictionary builder")
            sys.exit(1)
            
        if self.config.use_gunicorn and self.config.server_type == "gunicorn":
            self._run_gunicorn()
        else:
            self._run_wsgi_server()
            
    def _run_wsgi_server(self) -> None:
        """Run with built-in WSGI server."""
        try:
            self.logger.info(f"Starting {self.config.server_type} server on {self.config.host}:{self.config.port}")
            
            if self.config.server_type == "threaded":
                httpd = make_threaded_server(
                    self.config.host, 
                    self.config.port, 
                    self.wsgi_application,
                    max_threads=self.config.max_threads,
                    request_queue_size=self.config.request_queue_size
                )
                self.logger.info(f"Multi-threaded server (max_threads={self.config.max_threads}) ready at http://localhost:{self.config.port}/")
            else:
                httpd = make_server(self.config.host, self.config.port, self.wsgi_application)
                self.logger.info(f"Simple server ready at http://localhost:{self.config.port}/")
                
            httpd.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)
            
    def _run_gunicorn(self) -> None:
        """Run with Gunicorn for production."""
        try:
            self.logger.info(f"Starting Gunicorn server with {self.config.gunicorn_workers} workers")
            
            # Create a gunicorn app module
            app_module = f"{__name__}:create_app()"
            
            cmd = [
                "gunicorn",
                "--bind", f"{self.config.host}:{self.config.port}",
                "--workers", str(self.config.gunicorn_workers),
                "--threads", str(self.config.gunicorn_threads),
                "--timeout", str(self.config.connection_timeout),
                "--access-logfile", "-" if self.config.debug else "/dev/null",
                "--error-logfile", "-",
                "--worker-class", "gthread",
                app_module
            ]
            
            self.logger.info(f"Gunicorn command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            self.logger.error("Gunicorn not found. Install with: pip install gunicorn")
            self.logger.info("Falling back to threaded WSGI server...")
            self.config.server_type = "threaded"
            self._run_wsgi_server()
        except Exception as e:
            self.logger.error(f"Gunicorn error: {e}")
            sys.exit(1)


def create_app():
    """Create WSGI application for Gunicorn."""
    config = load_config()
    config.setup_logging()
    
    server = MDXServer(config)
    if not server._initialize_builder():
        raise RuntimeError("Failed to initialize dictionary builder")
    
    return server.wsgi_application


def main():
    """Main entry point."""
    # Load configuration from file and environment
    config = load_config()
    config.setup_logging()
    
    server = MDXServer(config)
    server.run()


if __name__ == "__main__":
    main()