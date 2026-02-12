"""Tests for config loading."""
import pytest

from app import load_config


def test_load_config_valid(tmp_path):
    """Valid YAML with media_root returns dict with that key."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("media_root: /var/media\n", encoding="utf-8")
    result = load_config(str(config_file))
    assert result == {"media_root": "/var/media"}


def test_load_config_empty_raises(tmp_path):
    """Empty YAML or missing media_root raises ValueError."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="media_root"):
        load_config(str(config_file))


def test_load_config_missing_key_raises(tmp_path):
    """YAML without media_root key raises ValueError."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("other_key: value\n", encoding="utf-8")
    with pytest.raises(ValueError, match="media_root"):
        load_config(str(config_file))


def test_load_config_missing_file_raises(tmp_path):
    """Missing config file raises FileNotFoundError (or OSError)."""
    missing = tmp_path / "does_not_exist.yaml"
    assert not missing.exists()
    with pytest.raises((FileNotFoundError, OSError)):
        load_config(str(missing))
