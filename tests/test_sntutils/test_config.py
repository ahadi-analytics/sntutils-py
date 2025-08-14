"""Tests for config module."""

import logging
from pathlib import Path
from unittest.mock import patch, mock_open

from sntutils.config import Config


class TestConfig:
    """Test Config class."""

    def test_default_config_values(self):
        """Test that default configuration values are correct."""
        config = Config()

        assert config.get("default_download_dir") == "~/data/chirps"
        assert config.get("chunk_size") == 8192
        assert config.get("timeout") == 60
        assert config.get("retry_times") == 3
        assert config.get("retry_delay") == 1.0
        assert config.get("retry_backoff") == 2.0
        assert config.get("log_level") == "INFO"

    def test_get_download_dir_expands_path(self):
        """Test that get_download_dir expands user path."""
        config = Config()
        download_dir = config.get_download_dir()

        assert isinstance(download_dir, Path)
        assert str(download_dir).startswith("/")  # Should be absolute path

    def test_get_retry_config(self):
        """Test retry configuration getter."""
        config = Config()
        retry_config = config.get_retry_config()

        assert retry_config["times"] == 3
        assert retry_config["delay"] == 1.0
        assert retry_config["backoff"] == 2.0

    def test_yaml_config_loading(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
default_download_dir: "/custom/path"
chunk_size: 16384
timeout: 120
retry_times: 5
log_level: "DEBUG"
"""

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open", mock_open(read_data=yaml_content)),
            patch("sntutils.config.YAML_AVAILABLE", True),
            patch("yaml.safe_load") as mock_yaml_load,
        ):

            # Mock that config file exists
            mock_exists.return_value = True
            mock_yaml_load.return_value = {
                "default_download_dir": "/custom/path",
                "chunk_size": 16384,
                "timeout": 120,
                "retry_times": 5,
                "log_level": "DEBUG",
            }

            config = Config()

            assert config.get("default_download_dir") == "/custom/path"
            assert config.get("chunk_size") == 16384
            assert config.get("timeout") == 120
            assert config.get("retry_times") == 5
            assert config.get("log_level") == "DEBUG"

    def test_config_without_yaml(self):
        """Test configuration when PyYAML is not available."""
        with (
            patch("sntutils.config.YAML_AVAILABLE", False),
            patch("pathlib.Path.exists") as mock_exists,
        ):

            mock_exists.return_value = True  # Config file exists but can't be loaded

            config = Config()

            # Should fall back to defaults
            assert config.get("chunk_size") == 8192
            assert config.get("timeout") == 60

    def test_setup_logging(self):
        """Test logging setup."""
        config = Config()

        with patch("logging.basicConfig") as mock_basic_config:
            config.setup_logging()

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == logging.INFO

    def test_config_file_search_order(self):
        """Test that configuration files are searched in correct order."""
        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("sntutils.config.Config._load_yaml_config") as mock_load,
        ):

            # Make the second path exist (loop will break after finding it)
            mock_exists.side_effect = [False, True, False, False]

            Config()

            # Should have tried to load the second config path
            mock_load.assert_called_once()

            # Check that exists was called twice (first False, second True, then break)
            assert mock_exists.call_count == 2

    def test_config_get_with_default(self):
        """Test config get method with default value."""
        config = Config()

        # Non-existent key should return default
        assert config.get("non_existent_key", "default_value") == "default_value"

        # Existing key should return actual value
        assert config.get("chunk_size", 999) == 8192

    def test_config_handles_yaml_load_error(self):
        """Test that config handles YAML loading errors gracefully."""
        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open", mock_open()),
            patch("sntutils.config.YAML_AVAILABLE", True),
            patch("yaml.safe_load") as mock_yaml_load,
            patch("sntutils.config.logger") as mock_logger,
        ):

            mock_exists.return_value = True
            mock_yaml_load.side_effect = Exception("YAML parse error")

            config = Config()

            # Should fall back to defaults and log warning
            assert config.get("chunk_size") == 8192
            mock_logger.warning.assert_called()
