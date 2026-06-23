"""Unit tests for password hashing and JWT tokens (Unit 2)."""
import time

import pytest

from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    TokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip_carries_scope():
    token = create_access_token(user_id="u1", role="ORG_ADMIN", tenant_id="t1")
    claims = decode_access_token(token)
    assert claims["sub"] == "u1"
    assert claims["role"] == "ORG_ADMIN"
    assert claims["tenant_id"] == "t1"
    assert claims["type"] == "access"


def test_super_admin_token_has_null_tenant():
    claims = decode_access_token(
        create_access_token(user_id="s1", role="SUPER_ADMIN", tenant_id=None)
    )
    assert claims["tenant_id"] is None


def test_tampered_token_rejected():
    token = create_access_token(user_id="u1", role="ORG_ADMIN", tenant_id="t1")
    with pytest.raises(TokenError):
        decode_access_token(token + "tampered")


def test_expired_token_rejected(monkeypatch):
    from app.security import tokens as tok

    monkeypatch.setattr(tok.settings, "access_token_ttl_seconds", -1)
    token = tok.create_access_token(user_id="u1", role="PARTICIPANT", tenant_id="t1")
    time.sleep(0.01)
    with pytest.raises(TokenError):
        tok.decode_access_token(token)


def test_refresh_token_hash_is_deterministic_and_opaque():
    t = generate_refresh_token()
    assert hash_refresh_token(t) == hash_refresh_token(t)
    assert hash_refresh_token(t) != t
