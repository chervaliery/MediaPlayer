"""Tests for config validation (_apply_config)."""
import pytest

from app import _apply_config


@pytest.fixture
def media_root(tmp_path):
    """A temporary directory usable as media_root."""
    return tmp_path.resolve()


def test_apply_config_valid_private_minimal(media_root):
    """Valid private with only media_root returns (Path, 'private')."""
    config = {"media_root": str(media_root)}
    root, mode = _apply_config(config)
    assert root == media_root
    assert mode == "private"


def test_apply_config_valid_private_with_database(media_root, tmp_path):
    """Valid private with database and share_default_expiry_seconds."""
    db_path = str(tmp_path / "shares.db")
    config = {
        "media_root": str(media_root),
        "database": db_path,
        "share_default_expiry_seconds": 86400,
    }
    root, mode = _apply_config(config)
    assert root == media_root
    assert mode == "private"


def test_apply_config_valid_public(media_root, tmp_path):
    """Valid public with media_root and database returns (Path, 'public')."""
    db_path = str(tmp_path / "shares.db")
    config = {
        "mode": "public",
        "media_root": str(media_root),
        "database": db_path,
    }
    root, mode = _apply_config(config)
    assert root == media_root
    assert mode == "public"


def test_apply_config_invalid_mode(media_root):
    """Invalid mode raises ValueError."""
    config = {"media_root": str(media_root), "mode": "invalid"}
    with pytest.raises(ValueError, match="mode must be 'private' or 'public'"):
        _apply_config(config)


def test_apply_config_public_without_database(media_root):
    """Public mode without database raises ValueError."""
    config = {"mode": "public", "media_root": str(media_root)}
    with pytest.raises(ValueError, match="database is required when mode is public"):
        _apply_config(config)


def test_apply_config_private_database_without_expiry(media_root, tmp_path):
    """Private with database but no share_default_expiry_seconds raises ValueError."""
    db_path = str(tmp_path / "shares.db")
    config = {"media_root": str(media_root), "database": db_path}
    with pytest.raises(
        ValueError,
        match="share_default_expiry_seconds required when database is set",
    ):
        _apply_config(config)


def test_apply_config_media_root_nonexistent(tmp_path):
    """Nonexistent media_root raises FileNotFoundError."""
    missing = tmp_path / "nonexistent"
    assert not missing.exists()
    config = {"media_root": str(missing)}
    with pytest.raises(FileNotFoundError, match="media_root does not exist"):
        _apply_config(config)
