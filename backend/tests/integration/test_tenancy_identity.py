"""Unit 2 integration tests: onboarding chain, auth, RBAC, tenant isolation.

Runs the real FastAPI app over an in-memory SQLite database (shared via
StaticPool), overriding the DB-session dependency. Validates the Unit 2
"done when" criteria end to end.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.models.base import Base, new_uuid
from app.models.user import User
from app.security.passwords import hash_password

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"


@pytest.fixture
async def api():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    # Seed the bootstrap Super Admin directly (mirrors the CLI seed).
    async with maker() as s:
        s.add(
            User(
                id=new_uuid(),
                tenant_id=None,
                email=SUPER_EMAIL,
                password_hash=hash_password(SUPER_PASSWORD),
                role="SUPER_ADMIN",
                first_name="Root",
                last_name="Admin",
            )
        )
        await s.commit()

    async def _override():
        async with maker() as s:
            yield s

    app.dependency_overrides[db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


async def _login(client, email, password, tenant_slug=None) -> dict:
    body = {"email": email, "password": password}
    if tenant_slug:
        body["tenant_slug"] = tenant_slug
    resp = await client.post("/auth/login", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_org(client, super_tokens, slug, admin_email) -> dict:
    resp = await client.post(
        "/organizations",
        headers=_auth(super_tokens),
        json={
            "name": f"Org {slug}",
            "slug": slug,
            "portal_url": f"https://{slug}.contestforge.test",
            "admin_email": admin_email,
            "admin_first_name": "Org",
            "admin_last_name": "Admin",
            "admin_password": "org-admin-pw-1",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_full_onboarding_chain(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    assert su["role"] == "SUPER_ADMIN"

    org = await _create_org(api, su, "acme", "admin@acme.com")
    assert org["slug"] == "acme"

    # Org Admin logs in with tenant hint and gets a tenant-scoped token.
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    assert oa["role"] == "ORG_ADMIN"

    # Org Admin creates a Participant.
    resp = await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "player@acme.com",
            "first_name": "Pat",
            "last_name": "Player",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "PARTICIPANT"

    # Participant can log in.
    pl = await _login(api, "player@acme.com", "player-pw-123", tenant_slug="acme")
    assert pl["role"] == "PARTICIPANT"


@pytest.mark.asyncio
async def test_create_user_rejects_super_admin_role(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    resp = await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "x@acme.com",
            "first_name": "X",
            "last_name": "Y",
            "role": "SUPER_ADMIN",
            "password": "whatever-123",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_refresh_rotates_and_detects_reuse(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    first_refresh = su["refresh_token"]

    r1 = await api.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert r1.status_code == 200
    assert r1.json()["refresh_token"] != first_refresh  # rotated

    # Reusing the now-revoked original refresh token is rejected.
    reuse = await api.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    out = await api.post("/auth/logout", json={"refresh_token": su["refresh_token"]})
    assert out.status_code == 204
    again = await api.post("/auth/refresh", json={"refresh_token": su["refresh_token"]})
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_rbac_participant_cannot_create_users(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "player@acme.com",
            "first_name": "Pat",
            "last_name": "Player",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    pl = await _login(api, "player@acme.com", "player-pw-123", tenant_slug="acme")
    resp = await api.post(
        "/users",
        headers=_auth(pl),
        json={
            "email": "n@acme.com",
            "first_name": "N",
            "last_name": "O",
            "role": "PARTICIPANT",
            "password": "nope-123456",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_org_admin_cannot_access_super_admin_endpoint(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    resp = await api.get("/organizations", headers=_auth(oa))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_user_isolation(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    await _create_org(api, su, "globex", "admin@globex.com")

    oa_acme = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    # Create a participant in globex via its own admin.
    oa_globex = await _login(api, "admin@globex.com", "org-admin-pw-1", tenant_slug="globex")
    created = await api.post(
        "/users",
        headers=_auth(oa_globex),
        json={
            "email": "g@globex.com",
            "first_name": "G",
            "last_name": "X",
            "role": "PARTICIPANT",
            "password": "globex-pw-123",
        },
    )
    globex_user_id = created.json()["id"]

    # Acme admin must not see globex's user.
    resp = await api.get(f"/users/{globex_user_id}", headers=_auth(oa_acme))
    assert resp.status_code == 404

    listing = await api.get("/users", headers=_auth(oa_acme))
    assert all(u["email"] != "g@globex.com" for u in listing.json())


# ── F5: bulk participant import ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_import_creates_participants_with_otps(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")

    resp = await api.post(
        "/users/bulk",
        headers=_auth(oa),
        json={
            "participants": [
                {"email": "a@acme.com", "first_name": "A", "last_name": "One"},
                {"email": "b@acme.com", "first_name": "B", "last_name": "Two"},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["created_count"] == 2
    assert data["skipped_count"] == 0
    otps = {r["email"]: r["one_time_password"] for r in data["results"]}
    assert all(otps.values())  # every CREATED row carries an OTP

    # A created participant can log in with the returned one-time password.
    pl = await _login(api, "a@acme.com", otps["a@acme.com"], tenant_slug="acme")
    assert pl["role"] == "PARTICIPANT"


@pytest.mark.asyncio
async def test_bulk_import_skips_duplicates_and_invalid(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")

    # Pre-existing participant collides with one import row.
    await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "dup@acme.com",
            "first_name": "D",
            "last_name": "Up",
            "role": "PARTICIPANT",
            "password": "existing-pw-1",
        },
    )

    resp = await api.post(
        "/users/bulk",
        headers=_auth(oa),
        json={
            "participants": [
                {"email": "dup@acme.com", "first_name": "D", "last_name": "Up"},  # exists
                {"email": "new@acme.com", "first_name": "N", "last_name": "Ew"},  # created
                {"email": "new@acme.com", "first_name": "N", "last_name": "Ew"},  # batch dup
                {"email": "not-an-email", "first_name": "X", "last_name": "Y"},  # invalid
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["created_count"] == 1
    assert data["skipped_count"] == 3
    reasons = {(r["email"], r["status"], r["reason"]) for r in data["results"]}
    assert ("dup@acme.com", "SKIPPED", "duplicate_email") in reasons
    assert ("new@acme.com", "SKIPPED", "duplicate_email") in reasons
    assert ("not-an-email", "SKIPPED", "invalid_email") in reasons


@pytest.mark.asyncio
async def test_bulk_import_rejects_participant_caller(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "player@acme.com",
            "first_name": "Pat",
            "last_name": "Player",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    pl = await _login(api, "player@acme.com", "player-pw-123", tenant_slug="acme")
    resp = await api.post(
        "/users/bulk",
        headers=_auth(pl),
        json={"participants": [{"email": "z@acme.com", "first_name": "Z", "last_name": "Z"}]},
    )
    assert resp.status_code == 403
