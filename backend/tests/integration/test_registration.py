"""Unit 6 integration tests: Registration.

Validates self-registration window, duplicate handling, roster listing, the
caller's own registration, withdrawal rules (self before close vs Org Admin), and
tenant isolation.
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
PW = "participant-pw-1"


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


async def _create_participant(client, oa, email) -> dict:
    resp = await client.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": email,
            "first_name": "Pat",
            "last_name": "Player",
            "role": "PARTICIPANT",
            "password": PW,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_contest(client, oa, name="quiz") -> dict:
    resp = await client.post(
        "/contests",
        headers=_auth(oa),
        json={"name": name, "description": "test", "structure": "NORMAL"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _transition(client, oa, contest_id, target) -> None:
    resp = await client.post(
        f"/contests/{contest_id}/lifecycle",
        headers=_auth(oa),
        json={"target_status": target},
    )
    assert resp.status_code == 200, resp.text


async def _open_contest(client, oa) -> dict:
    contest = await _create_contest(client, oa)
    await _transition(client, oa, contest["id"], "PUBLISHED")
    await _transition(client, oa, contest["id"], "REGISTRATION_OPEN")
    return contest


async def _setup(api):
    """Return (org_admin_tokens, participant_tokens, contest in REGISTRATION_OPEN)."""
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    await _create_participant(api, oa, "p1@acme.com")
    pt = await _login(api, "p1@acme.com", PW, tenant_slug="acme")
    contest = await _open_contest(api, oa)
    return oa, pt, contest


@pytest.mark.asyncio
async def test_self_register_and_get_me(api):
    _, pt, contest = await _setup(api)

    resp = await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "REGISTERED"
    assert data["spectator_access"] is False

    me = await api.get(f"/contests/{contest['id']}/registrations/me", headers=_auth(pt))
    assert me.status_code == 200
    assert me.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_register_only_when_open(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    await _create_participant(api, oa, "p1@acme.com")
    pt = await _login(api, "p1@acme.com", PW, tenant_slug="acme")

    # DRAFT contest — registration not open yet.
    contest = await _create_contest(api, oa)
    resp = await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_duplicate_registration_rejected(api):
    _, pt, contest = await _setup(api)
    first = await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    assert first.status_code == 201
    dup = await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    assert dup.status_code == 409, dup.text


@pytest.mark.asyncio
async def test_get_me_404_when_not_registered(api):
    _, pt, contest = await _setup(api)
    me = await api.get(f"/contests/{contest['id']}/registrations/me", headers=_auth(pt))
    assert me.status_code == 404


@pytest.mark.asyncio
async def test_admin_lists_registrations(api):
    oa, pt, contest = await _setup(api)
    await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))

    lst = await api.get(f"/contests/{contest['id']}/registrations", headers=_auth(oa))
    assert lst.status_code == 200
    assert len(lst.json()) == 1

    filtered = await api.get(
        f"/contests/{contest['id']}/registrations",
        headers=_auth(oa),
        params={"status": "REGISTERED"},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    empty = await api.get(
        f"/contests/{contest['id']}/registrations",
        headers=_auth(oa),
        params={"status": "COMPLETED"},
    )
    assert empty.status_code == 200
    assert empty.json() == []


@pytest.mark.asyncio
async def test_participant_cannot_list(api):
    _, pt, contest = await _setup(api)
    lst = await api.get(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    assert lst.status_code == 403


@pytest.mark.asyncio
async def test_participant_withdraws_before_close(api):
    _, pt, contest = await _setup(api)
    reg = (
        await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    ).json()

    delete = await api.delete(
        f"/contests/{contest['id']}/registrations/{reg['id']}", headers=_auth(pt)
    )
    assert delete.status_code == 204
    me = await api.get(f"/contests/{contest['id']}/registrations/me", headers=_auth(pt))
    assert me.status_code == 404


@pytest.mark.asyncio
async def test_participant_cannot_withdraw_after_close(api):
    oa, pt, contest = await _setup(api)
    reg = (
        await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    ).json()

    await _transition(api, oa, contest["id"], "REGISTRATION_CLOSED")
    delete = await api.delete(
        f"/contests/{contest['id']}/registrations/{reg['id']}", headers=_auth(pt)
    )
    assert delete.status_code == 409, delete.text


@pytest.mark.asyncio
async def test_org_admin_withdraws_after_close(api):
    oa, pt, contest = await _setup(api)
    reg = (
        await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    ).json()

    await _transition(api, oa, contest["id"], "REGISTRATION_CLOSED")
    delete = await api.delete(
        f"/contests/{contest['id']}/registrations/{reg['id']}", headers=_auth(oa)
    )
    assert delete.status_code == 204, delete.text


@pytest.mark.asyncio
async def test_participant_cannot_withdraw_others(api):
    oa, pt, contest = await _setup(api)
    await _create_participant(api, oa, "p2@acme.com")
    pt2 = await _login(api, "p2@acme.com", PW, tenant_slug="acme")

    reg = (
        await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))
    ).json()

    # p2 tries to withdraw p1's registration.
    delete = await api.delete(
        f"/contests/{contest['id']}/registrations/{reg['id']}", headers=_auth(pt2)
    )
    assert delete.status_code == 403, delete.text


@pytest.mark.asyncio
async def test_cross_tenant_registration_isolation(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    await _create_org(api, su, "globex", "admin@globex.com")

    oa_acme = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    await _create_participant(api, oa_acme, "p1@acme.com")
    pt = await _login(api, "p1@acme.com", PW, tenant_slug="acme")
    contest = await _open_contest(api, oa_acme)
    await api.post(f"/contests/{contest['id']}/registrations", headers=_auth(pt))

    oa_globex = await _login(api, "admin@globex.com", "org-admin-pw-1", tenant_slug="globex")
    resp = await api.get(
        f"/contests/{contest['id']}/registrations", headers=_auth(oa_globex)
    )
    # Other tenant cannot see this contest's roster (contest not found in tenant).
    assert resp.status_code == 404
