"""Tests for share_store (create, get, revoke, get_active_by_file_path)."""
import pytest
import share_store


@pytest.fixture
def db_path(tmp_path):
    """Temp SQLite DB path."""
    p = tmp_path / "shares.db"
    share_store.init(str(p))
    return str(p)


def test_create_share_returns_token(db_path):
    token = share_store.create_share(db_path, "sub/file.txt", 3600)
    assert isinstance(token, str)
    assert len(token) > 10


def test_get_by_token_found(db_path):
    token = share_store.create_share(db_path, "sub/file.txt", None)
    row = share_store.get_by_token(db_path, token)
    assert row is not None
    assert row["token"] == token
    assert row["file_path"] == "sub/file.txt"
    assert row["revoked_at"] is None


def test_get_by_token_not_found(db_path):
    assert share_store.get_by_token(db_path, "nonexistent") is None


def test_get_active_by_file_path_returns_latest(db_path):
    token1 = share_store.create_share(db_path, "a.txt", 3600)
    token2 = share_store.create_share(db_path, "a.txt", 3600)
    row = share_store.get_active_by_file_path(db_path, "a.txt")
    assert row is not None
    assert row["file_path"] == "a.txt"
    assert row["token"] in (token1, token2)


def test_get_active_by_file_path_none_when_revoked(db_path):
    token = share_store.create_share(db_path, "b.txt", None)
    share_store.revoke(db_path, token)
    assert share_store.get_active_by_file_path(db_path, "b.txt") is None


def test_revoke_returns_true(db_path):
    token = share_store.create_share(db_path, "c.txt", None)
    assert share_store.revoke(db_path, token) is True
    row = share_store.get_by_token(db_path, token)
    assert row["revoked_at"] is not None


def test_revoke_idempotent_returns_false(db_path):
    token = share_store.create_share(db_path, "d.txt", None)
    share_store.revoke(db_path, token)
    assert share_store.revoke(db_path, token) is False


def test_is_share_active_false_when_revoked(db_path):
    token = share_store.create_share(db_path, "e.txt", None)
    row = share_store.get_by_token(db_path, token)
    assert share_store.is_share_active(row) is True
    share_store.revoke(db_path, token)
    row = share_store.get_by_token(db_path, token)
    assert share_store.is_share_active(row) is False
