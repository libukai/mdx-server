#!/usr/bin/env python3
"""
Configuration management for MDX Server.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ServerConfig:
    """Server configuration with validation."""
    
    # Server settings
    host: str = ""
    port: int = 8000
    debug: bool = False
    
    # Directory settings
    dict_directory: str = "dict"
    resource_directory: str = "mdx"
    
    # Performance settings
    cache_enabled: bool = True
    max_word_length: int = 100
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Concurrency settings
    server_type: str = "threaded"  # "simple", "threaded", "gunicorn"
    max_threads: int = 20
    request_queue_size: int = 50
    connection_timeout: int = 30
    
    # Gunicorn settings
    use_gunicorn: bool = False
    gunicorn_workers: int = 4
    gunicorn_threads: int = 5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
        
    def validate(self) -> None:
        """Validate configuration values."""
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port number: {self.port}")
            
        if self.max_word_length < 1:
            raise ValueError("max_word_length must be positive")
            
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")
            
        if self.server_type not in ["simple", "threaded", "gunicorn"]:
            raise ValueError(f"Invalid server type: {self.server_type}")
            
        if self.max_threads < 1:
            raise ValueError("max_threads must be positive")
            
        if self.request_queue_size < 1:
            raise ValueError("request_queue_size must be positive")
            
        if self.gunicorn_workers < 1:
            raise ValueError("gunicorn_workers must be positive")
            
        if self.gunicorn_threads < 1:
            raise ValueError("gunicorn_threads must be positive")
            
    @classmethod
    def from_file(cls, config_path: Path) -> 'ServerConfig':
        """Load configuration from JSON file."""
        if not config_path.exists():
            logging.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Invalid config file {config_path}: {e}")
            return cls()
            
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("MDX_HOST", ""),
            port=int(os.getenv("MDX_PORT", "8000")),
            debug=os.getenv("MDX_DEBUG", "false").lower() == "true",
            dict_directory=os.getenv("MDX_DICT_DIR", "dict"),
            resource_directory=os.getenv("MDX_RESOURCE_DIR", "mdx"),
            cache_enabled=os.getenv("MDX_CACHE", "true").lower() == "true",
            max_word_length=int(os.getenv("MDX_MAX_WORD_LENGTH", "100")),
            log_level=os.getenv("MDX_LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("MDX_LOG_FILE"),
        )
        
    def to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2)
            
    def setup_logging(self) -> None:
        """Setup logging based on configuration."""
        level = getattr(logging, self.log_level)
        
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        handlers.append(console_handler)
        
        # File handler if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(level)
            handlers.append(file_handler)
            
        # Configure logging
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
            force=True
        )


def load_config() -> ServerConfig:
    """Load configuration from multiple sources with priority."""
    base_path = Path(__file__).parent
    
    # 1. Try loading from config file
    config_file = base_path / "config.json"
    config = ServerConfig.from_file(config_file)
    
    # 2. Override with environment variables if set
    env_overrides = {}
    for key in ["host", "port", "debug", "dict_directory", "resource_directory", 
                "cache_enabled", "max_word_length", "log_level", "log_file"]:
        env_key = f"MDX_{key.upper()}"
        if env_key in os.environ:
            value = os.environ[env_key]
            
            # Type conversion
            if key in ["port", "max_word_length"]:
                value = int(value)
            elif key in ["debug", "cache_enabled"]:
                value = value.lower() == "true"
                
            env_overrides[key] = value
            
    # Apply overrides
    for key, value in env_overrides.items():
        setattr(config, key, value)
        
    # Validate final configuration
    config.validate()
    
    return config