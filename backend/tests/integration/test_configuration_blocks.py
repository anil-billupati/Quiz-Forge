"""F8 integration tests: ConfigurationBlock authoring.

Validates CRUD, mode/scoring consistency, Draft-only editing, structure/scope
rules, and tenant isolation.
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


async def _create_normal_contest(client, org_admin_tokens, slug="quiz") -> dict:
    resp = await client.post(
        "/contests",
        headers=_auth(org_admin_tokens),
        json={
            "name": slug,
            "description": "test",
            "structure": "NORMAL",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_grouped_contest(client, org_admin_tokens, slug="grouped-quiz") -> dict:
    resp = await client.post(
        "/contests",
        headers=_auth(org_admin_tokens),
        json={
            "name": slug,
            "description": "test",
            "structure": "GROUPED",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_group(client, org_admin_tokens, contest_id, sequence=1) -> dict:
    resp = await client.post(
        f"/contests/{contest_id}/groups",
        headers=_auth(org_admin_tokens),
        json={"name": f"Group {sequence}", "sequence": sequence, "weight": None},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_set_and_get_contest_configuration(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)

    cfg = {
        "mode": "STANDARD",
        "question_duration_s": 20,
        "question_interval_s": 3,
        "explanation_duration_s": 5,
        "leaderboard_duration_s": 5,
        "reveal_mode": "AUTOMATIC",
        "ranking_criterion": "SCORE_ONLY",
        "tie_display": "SHARED_RANK",
        "leaderboard_visibility": "POST_QUESTION",
        "update_frequency": "PER_QUESTION",
        "survivor_score_reset": False,
        "scoring_config": {"correct_points": 10, "second_chance_rate": 0.5},
    }
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=cfg,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "STANDARD"
    assert data["scoring_model"] == "FIXED"
    assert data["scoring_config"]["correct_points"] == 10

    get_resp = await api.get(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa)
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_speed_mode_requires_time_based_scoring(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)

    bad = {
        "mode": "SPEED",
        "scoring_config": {"correct_points": 10, "second_chance_rate": 0.5},
    }
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=bad
    )
    assert resp.status_code == 422

    good = {
        "mode": "SPEED",
        "question_duration_s": 30,
        "scoring_config": {
            "bands": [
                {"max_seconds": 5, "points": 100},
                {"max_seconds": 10, "points": 75},
                {"max_seconds": 15, "points": 50},
                {"max_seconds": 20, "points": 25},
                {"max_seconds": 9999, "points": 10},
            ]
        },
    }
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=good
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scoring_model"] == "TIME_BASED"


@pytest.mark.asyncio
async def test_standard_mode_rejects_time_based_scoring(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)

    bad = {
        "mode": "STANDARD",
        "scoring_config": {
            "bands": [{"max_seconds": 5, "points": 100}, {"max_seconds": 9999, "points": 10}]
        },
    }
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=bad
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_configuration_locked_after_publish(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)

    cfg = {"mode": "STANDARD"}
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=cfg
    )
    assert resp.status_code == 200

    # Publish the contest.
    pub = await api.post(
        f"/contests/{contest['id']}/lifecycle",
        headers=_auth(oa),
        json={"target_status": "PUBLISHED"},
    )
    assert pub.status_code == 200

    # Configuration edits are now blocked.
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=cfg
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_group_configuration(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_grouped_contest(api, oa)
    group = await _create_group(api, oa, contest["id"])

    cfg = {
        "mode": "ELIMINATION",
        "elimination_combine_operator": "OR",
        "scoring_config": {"correct_points": 10, "second_chance_rate": 0.5},
    }
    resp = await api.put(
        f"/contests/{contest['id']}/groups/{group['id']}/configuration",
        headers=_auth(oa),
        json=cfg,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "ELIMINATION"
    assert data["elimination_combine_operator"] == "OR"


@pytest.mark.asyncio
async def test_cross_tenant_configuration_isolation(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    await _create_org(api, su, "globex", "admin@globex.com")

    oa_acme = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa_acme)

    cfg = {"mode": "STANDARD"}
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa_acme), json=cfg
    )
    block_id = resp.json()["id"]

    oa_globex = await _login(api, "admin@globex.com", "org-admin-pw-1", tenant_slug="globex")
    resp = await api.get(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa_globex)
    )
    assert resp.status_code == 404

    resp = await api.get(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa_acme)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == block_id
