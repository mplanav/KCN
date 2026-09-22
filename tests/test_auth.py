"""Tests de autenticación."""

import pytest

from kcn.auth import repo as auth


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("KCN_DATA_DIR", str(tmp_path))


def test_create_and_verify():
    auth.create_user("Marc", "secreto")
    assert auth.verify_user("marc", "secreto") is True
    assert auth.verify_user("marc", "malo") is False


def test_duplicate_user():
    auth.create_user("ana", "x")
    with pytest.raises(ValueError):
        auth.create_user("ANA", "y")


def test_unknown_user():
    assert auth.verify_user("nadie", "x") is False


def test_user_db_paths_differ():
    assert auth.user_db_path("marc") != auth.user_db_path("ana")
