import pytest

from app import db
from app.models.user import User


def test_password_is_hashed_with_bcrypt(app):
    user = User(email="a@test.sn", full_name="A", role="admin")
    user.set_password("MotDePasse123")

    assert user.password_hash != "MotDePasse123"
    assert user.password_hash.startswith("$2b$")


def test_check_password(app):
    user = User(email="a@test.sn", full_name="A", role="admin")
    user.set_password("MotDePasse123")

    assert user.check_password("MotDePasse123") is True
    assert user.check_password("autre-mot-de-passe") is False


def test_same_password_gives_different_hashes(app):
    u1 = User(email="a@test.sn", full_name="A", role="admin")
    u2 = User(email="b@test.sn", full_name="B", role="admin")
    u1.set_password("MotDePasse123")
    u2.set_password("MotDePasse123")

    assert u1.password_hash != u2.password_hash


def test_password_too_long_is_rejected(app):
    user = User(email="a@test.sn", full_name="A", role="admin")

    with pytest.raises(ValueError):
        user.set_password("x" * 73)


def test_check_password_with_invalid_hash_returns_false(app):
    user = User(email="a@test.sn", full_name="A", role="admin")
    user.password_hash = "pas-un-hash"

    assert user.check_password("MotDePasse123") is False


def test_user_defaults(app):
    user = User(email="a@test.sn", full_name="A")
    user.set_password("MotDePasse123")
    db.session.add(user)
    db.session.commit()

    assert user.role == "magasinier"
    assert user.is_active is True
    assert user.created_at is not None
