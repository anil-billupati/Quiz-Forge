"""F6 integration tests: contest CRUD + lifecycle state machine.

Runs the real FastAPI app over an in-memory SQLite database, overriding the
DB-session dependency. Validates the lifecycle invariants (BR-5), Draft-only
edit/delete, RBAC, and tenant isolation.
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


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _login(client, email, password, tenant_slug=None) -> dict:
    body = {"email": email, "password": password}
    if tenant_slug:
        body["tenant_slug"] = tenant_slug
    resp = await client.post("/auth/login", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _org_admin(client, slug, admin_email) -> dict:
    su = await _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    resp = await client.post(
        "/organizations",
        headers=_auth(su),
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
    return await _login(client, admin_email, "org-admin-pw-1", tenant_slug=slug)


async def _create_contest(client, oa, **overrides) -> dict:
    body = {"name": "Quiz", "structure": "NORMAL"}
    body.update(overrides)
    resp = await client.post("/contests", headers=_auth(oa), json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_and_full_lifecycle(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    contest = await _create_contest(api, oa, name="Cert Exam", structure="NORMAL")
    assert contest["lifecycle_status"] == "DRAFT"
    cid = contest["id"]

    # Advance through the full, non-skippable sequence.
    steps = ["PUBLISHED", "REGISTRATION_OPEN", "REGISTRATION_CLOSED"]
    for target in steps:
        resp = await api.post(
            f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": target}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["lifecycle_status"] == target

    # SCHEDULED requires a start time.
    resp = await api.post(
        f"/contests/{cid}/lifecycle",
        headers=_auth(oa),
        json={"target_status": "SCHEDULED", "scheduled_start_at": "2026-07-01T10:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scheduled_start_at"] is not None

    for target in ["LIVE", "COMPLETED", "ARCHIVED"]:
        resp = await api.post(
            f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": target}
        )
        assert resp.status_code == 200, resp.text
    final = await api.get(f"/contests/{cid}", headers=_auth(oa))
    assert final.json()["lifecycle_status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_illegal_transition_is_rejected(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    contest = await _create_contest(api, oa)
    cid = contest["id"]
    # Skipping PUBLISHED (DRAFT -> REGISTRATION_OPEN) is illegal.
    resp = await api.post(
        f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": "REGISTRATION_OPEN"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT_INVALID_TRANSITION"


@pytest.mark.asyncio
async def test_scheduled_requires_start_time(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = (await _create_contest(api, oa))["id"]
    for target in ["PUBLISHED", "REGISTRATION_OPEN", "REGISTRATION_CLOSED"]:
        await api.post(
            f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": target}
        )
    resp = await api.post(
        f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": "SCHEDULED"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT_MISSING_START"


@pytest.mark.asyncio
async def test_edit_and_delete_are_draft_only(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = (await _create_contest(api, oa))["id"]

    # Draft: edit allowed.
    resp = await api.patch(f"/contests/{cid}", headers=_auth(oa), json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"

    # Publish, then edit/delete must be rejected.
    await api.post(
        f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": "PUBLISHED"}
    )
    edit = await api.patch(f"/contests/{cid}", headers=_auth(oa), json={"name": "Nope"})
    assert edit.status_code == 409
    delete = await api.delete(f"/contests/{cid}", headers=_auth(oa))
    assert delete.status_code == 409


@pytest.mark.asyncio
async def test_delete_draft_contest(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = (await _create_contest(api, oa))["id"]
    assert (await api.delete(f"/contests/{cid}", headers=_auth(oa))).status_code == 204
    assert (await api.get(f"/contests/{cid}", headers=_auth(oa))).status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_contest_isolation(api):
    oa_acme = await _org_admin(api, "acme", "admin@acme.com")
    oa_globex = await _org_admin(api, "globex", "admin@globex.com")
    globex_contest = await _create_contest(api, oa_globex, name="Globex Cup")

    # Acme admin must not see globex's contest.
    resp = await api.get(f"/contests/{globex_contest['id']}", headers=_auth(oa_acme))
    assert resp.status_code == 404
    listing = await api.get("/contests", headers=_auth(oa_acme))
    assert all(c["name"] != "Globex Cup" for c in listing.json())


@pytest.mark.asyncio
async def test_rbac_participant_cannot_create_contest(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "p@acme.com",
            "first_name": "P",
            "last_name": "P",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    pl = await _login(api, "p@acme.com", "player-pw-123", tenant_slug="acme")
    resp = await api.post("/contests", headers=_auth(pl), json={"name": "X", "structure": "NORMAL"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_participant_can_browse_visible_contests(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    await api.post(
        "/users",
        headers=_auth(oa),
        json={
            "email": "p@acme.com",
            "first_name": "P",
            "last_name": "P",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    pl = await _login(api, "p@acme.com", "player-pw-123", tenant_slug="acme")

    draft = await _create_contest(api, oa, name="Draft Cup", structure="NORMAL")
    published = await _create_contest(api, oa, name="Open Cup", structure="NORMAL")
    await api.post(
        f"/contests/{published['id']}/lifecycle",
        headers=_auth(oa),
        json={"target_status": "PUBLISHED"},
    )

    resp = await api.get("/contests", headers=_auth(pl))
    assert resp.status_code == 200, resp.text
    visible = resp.json()
    assert all(c["name"] != "Draft Cup" for c in visible)
    assert any(c["name"] == "Open Cup" for c in visible)


@pytest.mark.asyncio
async def test_participant_browse_is_tenant_isolated(api):
    oa_acme = await _org_admin(api, "acme", "admin@acme.com")
    oa_globex = await _org_admin(api, "globex", "admin@globex.com")

    await api.post(
        "/users",
        headers=_auth(oa_acme),
        json={
            "email": "p@acme.com",
            "first_name": "P",
            "last_name": "P",
            "role": "PARTICIPANT",
            "password": "player-pw-123",
        },
    )
    pl = await _login(api, "p@acme.com", "player-pw-123", tenant_slug="acme")

    acme_pub = await _create_contest(api, oa_acme, name="Acme Open", structure="NORMAL")
    await api.post(
        f"/contests/{acme_pub['id']}/lifecycle",
        headers=_auth(oa_acme),
        json={"target_status": "PUBLISHED"},
    )
    globex_pub = await _create_contest(api, oa_globex, name="Globex Open", structure="NORMAL")
    await api.post(
        f"/contests/{globex_pub['id']}/lifecycle",
        headers=_auth(oa_globex),
        json={"target_status": "PUBLISHED"},
    )

    resp = await api.get("/contests", headers=_auth(pl))
    assert resp.status_code == 200, resp.text
    names = {c["name"] for c in resp.json()}
    assert "Acme Open" in names
    assert "Globex Open" not in names
