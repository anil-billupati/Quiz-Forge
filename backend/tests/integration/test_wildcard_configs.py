"""F9 integration tests: WildcardConfig authoring."""
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


async def _create_normal_contest(client, org_admin_tokens) -> dict:
    resp = await client.post(
        "/contests",
        headers=_auth(org_admin_tokens),
        json={"name": "quiz", "description": "test", "structure": "NORMAL"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_config(client, org_admin_tokens, contest_id) -> dict:
    resp = await client.put(
        f"/contests/{contest_id}/configuration",
        headers=_auth(org_admin_tokens),
        json={"mode": "STANDARD"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_list_update_delete_wildcard_config(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)
    block = await _set_config(api, oa, contest["id"])

    resp = await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa),
        json={"type": "FIFTY_FIFTY", "eligibility": "ALL"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "FIFTY_FIFTY"
    assert data["eligibility"] == "ALL"

    list_resp = await api.get(
        f"/configuration-blocks/{block['id']}/wildcards", headers=_auth(oa)
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    patch_resp = await api.patch(
        f"/configuration-blocks/{block['id']}/wildcards/FIFTY_FIFTY",
        headers=_auth(oa),
        json={"eligibility": "TOP_50_PERCENT"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["eligibility"] == "TOP_50_PERCENT"

    del_resp = await api.delete(
        f"/configuration-blocks/{block['id']}/wildcards/FIFTY_FIFTY", headers=_auth(oa)
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_wildcard_type_rejected(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)
    block = await _set_config(api, oa, contest["id"])

    resp = await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa),
        json={"type": "SKIP"},
    )
    assert resp.status_code == 201

    resp = await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa),
        json={"type": "SKIP"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invalid_wildcard_type_rejected(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)
    block = await _set_config(api, oa, contest["id"])

    resp = await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa),
        json={"type": "FREEZE_TIME"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_wildcard_config_locked_after_publish(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)
    block = await _set_config(api, oa, contest["id"])

    await api.post(
        f"/contests/{contest['id']}/lifecycle",
        headers=_auth(oa),
        json={"target_status": "PUBLISHED"},
    )

    resp = await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa),
        json={"type": "SECOND_CHANCE"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cross_tenant_wildcard_isolation(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    await _create_org(api, su, "globex", "admin@globex.com")

    oa_acme = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa_acme)
    block = await _set_config(api, oa_acme, contest["id"])

    await api.post(
        f"/configuration-blocks/{block['id']}/wildcards",
        headers=_auth(oa_acme),
        json={"type": "FIFTY_FIFTY"},
    )

    oa_globex = await _login(api, "admin@globex.com", "org-admin-pw-1", tenant_slug="globex")
    resp = await api.get(
        f"/configuration-blocks/{block['id']}/wildcards", headers=_auth(oa_globex)
    )
    assert resp.status_code == 404
