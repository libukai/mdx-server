#!/usr/bin/env python3
"""
Configuration management for MDX Server.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class DictConfig:
    """Single dictionary configuration."""

    name: str
    path: str
    route: str = ""
    enabled: bool = True


@dataclass
class ServerConfig:
    """Server configuration with validation."""

    # Server settings
    host: str = ""
    port: int = 8000
    debug: bool = False

    # Directory settings
    dict_directory: str = "/dict" if Path("/dict").exists() else "dict"
    resource_directory: str = "mdx"

    # Multi-dictionary settings
    dictionaries: dict[str, DictConfig] = field(default_factory=dict)

    # Performance settings
    cache_enabled: bool = True
    max_word_length: int = 100

    # Logging settings
    log_level: str = "INFO"
    log_file: str | None = None

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
    def from_file(cls, config_path: Path) -> "ServerConfig":
        """Load configuration from JSON file."""
        if not config_path.exists():
            logging.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            # 处理多词典配置
            if "dictionaries" in data:
                # 创建临时配置实例用于路径解析
                temp_config = cls(**{k: v for k, v in data.items() if k != "dictionaries"})
                
                dict_configs = {}
                for dict_id, dict_data in data["dictionaries"].items():
                    if isinstance(dict_data, dict):
                        # 解析字典路径
                        resolved_path = temp_config.resolve_dict_path(dict_data.get("path", ""))
                        dict_data_copy = dict_data.copy()
                        dict_data_copy["path"] = resolved_path
                        dict_configs[dict_id] = DictConfig(**dict_data_copy)
                    else:
                        # 简化配置格式兼容
                        resolved_path = temp_config.resolve_dict_path(str(dict_data))
                        dict_configs[dict_id] = DictConfig(
                            name=dict_id,
                            path=resolved_path,
                            route=dict_id if dict_id != "default" else "",
                        )
                data["dictionaries"] = dict_configs

            return cls(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Invalid config file {config_path}: {e}")
            return cls()

    @classmethod
    def from_env(cls) -> "ServerConfig":
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
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def resolve_dict_path(self, dict_path: str) -> str:
        """Resolve dictionary path considering Docker and local environments."""
        # 如果是绝对路径，直接返回
        if Path(dict_path).is_absolute():
            return dict_path
        
        # 相对路径处理：优先检查 /dict (Docker), 然后 dict (本地)
        possible_paths = [
            Path("/dict") / dict_path,  # Docker 环境
            Path("dict") / dict_path,   # 本地环境
            Path(dict_path),            # 当前目录相对路径
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # 如果都不存在，根据环境返回最可能的路径
        if Path("/dict").exists():
            return str(Path("/dict") / dict_path)  # Docker 环境
        else:
            return str(Path("dict") / dict_path)   # 本地环境

    def auto_discover_dictionaries(self) -> None:
        """Auto-discover MDX files if no dictionaries configured."""
        if self.dictionaries:
            return  # 已有配置，不自动发现

        dict_path = Path(self.dict_directory)
        if not dict_path.exists():
            return

        # 扫描 MDX 文件
        for mdx_file in dict_path.glob("*.mdx"):
            dict_id = mdx_file.stem
            route = dict_id if dict_id != "default" else ""

            self.dictionaries[dict_id] = DictConfig(
                name=dict_id.replace("_", " ").title(),
                path=str(mdx_file),
                route=route,
                enabled=True,
            )

        logging.info(f"Auto-discovered {len(self.dictionaries)} dictionaries")

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
            handlers.append(file_handler)  # type: ignore[arg-type]

        # Configure logging
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
            force=True,
        )


def load_config() -> ServerConfig:
    """Load configuration from multiple sources with priority."""
    # 配置文件查找优先级
    config_paths = [
        Path("/app/config.json"),  # 1. Docker 环境
        Path(__file__).parent.parent / "config.json",  # 2. 项目根目录 (开发环境)
        Path(__file__).parent / "config.json",  # 3. mdx_server/ 目录 (兼容旧版本)
    ]
    
    config_file = None
    for path in config_paths:
        if path.exists():
            config_file = path
            break
    
    # 如果都找不到，使用默认配置
    if config_file is None:
        config_file = config_paths[1]  # 使用项目根目录作为默认路径

    config = ServerConfig.from_file(config_file)

    # 2. Override with environment variables if set
    env_overrides: dict[str, str | int | bool] = {}
    for key in [
        "host",
        "port",
        "debug",
        "dict_directory",
        "resource_directory",
        "cache_enabled",
        "max_word_length",
        "log_level",
        "log_file",
    ]:
        env_key = f"MDX_{key.upper()}"
        if env_key in os.environ:
            value = os.environ[env_key]

            # Type conversion
            if key in ["port", "max_word_length"]:
                env_overrides[key] = int(value)
            elif key in ["debug", "cache_enabled"]:
                env_overrides[key] = value.lower() == "true"
            else:
                env_overrides[key] = value  # type: ignore[assignment]

    # Apply overrides individually with type safety
    if "host" in env_overrides:
        config.host = env_overrides["host"]  # type: ignore[assignment]
    if "port" in env_overrides:
        config.port = env_overrides["port"]  # type: ignore[assignment]
    if "debug" in env_overrides:
        config.debug = env_overrides["debug"]  # type: ignore[assignment]
    if "dict_directory" in env_overrides:
        config.dict_directory = env_overrides["dict_directory"]  # type: ignore[assignment]
    if "resource_directory" in env_overrides:
        config.resource_directory = env_overrides["resource_directory"]  # type: ignore[assignment]
    if "cache_enabled" in env_overrides:
        config.cache_enabled = env_overrides["cache_enabled"]  # type: ignore[assignment]
    if "max_word_length" in env_overrides:
        config.max_word_length = env_overrides["max_word_length"]  # type: ignore[assignment]
    if "log_level" in env_overrides:
        config.log_level = env_overrides["log_level"]  # type: ignore[assignment]
    if "log_file" in env_overrides:
        config.log_file = env_overrides["log_file"]  # type: ignore[assignment]

    # Validate final configuration
    config.validate()

    return config
