"""F7 integration tests: groups for GROUPED contests.

Validates GROUPED-only + Draft-only editing, unique sequence, RBAC, and tenant
isolation. Runs the app over in-memory SQLite with the DB session overridden.
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


async def _contest(client, oa, structure="GROUPED") -> str:
    body = {"name": "Challenge", "structure": structure}
    if structure == "GROUPED":
        body["group_score_rollup"] = "SUM"
    resp = await client.post("/contests", headers=_auth(oa), json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_and_list_groups(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa, structure="GROUPED")

    g1 = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa),
        json={"name": "Aptitude", "sequence": 1},
    )
    assert g1.status_code == 201, g1.text
    g2 = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa),
        json={"name": "Java", "sequence": 2, "weight": 2.0},
    )
    assert g2.status_code == 201

    listing = await api.get(f"/contests/{cid}/groups", headers=_auth(oa))
    names = [g["name"] for g in listing.json()]
    assert names == ["Aptitude", "Java"]  # ordered by sequence
    assert listing.json()[1]["weight"] == 2.0


@pytest.mark.asyncio
async def test_groups_rejected_on_normal_contest(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa, structure="NORMAL")
    resp = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "X", "sequence": 1}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT_NOT_GROUPED"


@pytest.mark.asyncio
async def test_duplicate_sequence_rejected(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa)
    await api.post(f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "A", "sequence": 1})
    dup = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "B", "sequence": 1}
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT_SEQUENCE"


@pytest.mark.asyncio
async def test_update_and_delete_group(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa)
    created = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "Old", "sequence": 1}
    )
    gid = created.json()["id"]

    upd = await api.patch(
        f"/contests/{cid}/groups/{gid}", headers=_auth(oa),
        json={"name": "New", "sequence": 5, "weight": 1.5},
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "New" and upd.json()["sequence"] == 5

    delete = await api.delete(f"/contests/{cid}/groups/{gid}", headers=_auth(oa))
    assert delete.status_code == 204
    assert (await api.get(f"/contests/{cid}/groups", headers=_auth(oa))).json() == []


@pytest.mark.asyncio
async def test_groups_editable_only_in_draft(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa)
    await api.post(f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "A", "sequence": 1})
    # Publish, then group create must be rejected.
    await api.post(
        f"/contests/{cid}/lifecycle", headers=_auth(oa), json={"target_status": "PUBLISHED"}
    )
    resp = await api.post(
        f"/contests/{cid}/groups", headers=_auth(oa), json={"name": "B", "sequence": 2}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT_NOT_DRAFT"


@pytest.mark.asyncio
async def test_cross_tenant_group_isolation(api):
    oa_acme = await _org_admin(api, "acme", "admin@acme.com")
    oa_globex = await _org_admin(api, "globex", "admin@globex.com")
    gx_cid = await _contest(api, oa_globex)
    await api.post(
        f"/contests/{gx_cid}/groups", headers=_auth(oa_globex), json={"name": "GX", "sequence": 1}
    )
    # Acme admin cannot see globex's contest/groups (contest 404 in acme's tenant).
    resp = await api.get(f"/contests/{gx_cid}/groups", headers=_auth(oa_acme))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rbac_participant_cannot_create_group(api):
    oa = await _org_admin(api, "acme", "admin@acme.com")
    cid = await _contest(api, oa)
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
    resp = await api.post(
        f"/contests/{cid}/groups", headers=_auth(pl), json={"name": "X", "sequence": 1}
    )
    assert resp.status_code == 403
