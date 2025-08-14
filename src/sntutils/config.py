"""Configuration management for sntutils."""

import logging
from pathlib import Path
from typing import Dict, Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "default_download_dir": "~/data/chirps",
    "chunk_size": 8192,
    "timeout": 60,
    "retry_times": 3,
    "retry_delay": 1.0,
    "retry_backoff": 2.0,
    "log_level": "INFO",
}


class Config:
    """Configuration manager for sntutils."""

    def __init__(self) -> None:
        self._config = DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file if it exists."""
        config_paths = [
            Path.home() / ".sntutils" / "config.yaml",
            Path.home() / ".sntutils" / "config.yml",
            Path.cwd() / ".sntutils.yaml",
            Path.cwd() / ".sntutils.yml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    self._load_yaml_config(config_path)
                    logger.info(f"Loaded configuration from {config_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")

    def _load_yaml_config(self, config_path: Path) -> None:
        """Load YAML configuration file."""
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, skipping YAML config file")
            return

        with open(config_path, "r") as f:
            file_config = yaml.safe_load(f)

        if file_config:
            self._config.update(file_config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def get_download_dir(self) -> Path:
        """Get expanded download directory path."""
        download_dir = self.get("default_download_dir", "~/data/chirps")
        return Path(download_dir).expanduser()

    def get_chunk_size(self) -> int:
        """Get download chunk size."""
        return int(self.get("chunk_size", 8192))

    def get_timeout(self) -> int:
        """Get request timeout."""
        return int(self.get("timeout", 60))

    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return {
            "times": self.get("retry_times", 3),
            "delay": self.get("retry_delay", 1.0),
            "backoff": self.get("retry_backoff", 2.0),
        }

    def setup_logging(self) -> None:
        """Setup logging based on configuration."""
        log_level = self.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global configuration instance
config = Config()
