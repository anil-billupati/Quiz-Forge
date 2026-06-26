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
        "elimination_rules": [{"type": "FIRST_WRONG"}],
        "checkpoints": [{"type": "AFTER_GROUP"}],
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
    assert len(data["elimination_rules"]) == 1
    assert len(data["checkpoints"]) == 1


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


# --- Elimination configuration (BR-4) -------------------------------------


def _elimination_cfg(**overrides) -> dict:
    cfg = {
        "mode": "ELIMINATION",
        "elimination_combine_operator": "AND",
        "elimination_rules": [
            {"type": "N_WRONG", "n_value": 2},
            {"type": "BOTTOM_X_PERCENT", "percent_value": 10},
        ],
        "checkpoints": [
            {"type": "AFTER_QUESTION", "question_sequence": 5},
            {"type": "AFTER_GROUP"},
        ],
        "scoring_config": {"correct_points": 10, "second_chance_rate": 0.5},
    }
    cfg.update(overrides)
    return cfg


async def _elimination_contest(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    oa = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_normal_contest(api, oa)
    return oa, contest


@pytest.mark.asyncio
async def test_elimination_config_persists_and_reads_back(api):
    oa, contest = await _elimination_contest(api)

    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=_elimination_cfg()
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "ELIMINATION"
    assert data["elimination_combine_operator"] == "AND"
    assert {r["type"] for r in data["elimination_rules"]} == {"N_WRONG", "BOTTOM_X_PERCENT"}
    assert {c["type"] for c in data["checkpoints"]} == {"AFTER_QUESTION", "AFTER_GROUP"}

    get_resp = await api.get(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa)
    )
    assert get_resp.status_code == 200
    assert len(get_resp.json()["elimination_rules"]) == 2
    assert len(get_resp.json()["checkpoints"]) == 2


@pytest.mark.asyncio
async def test_elimination_missing_rules_rejected(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(elimination_rules=[]),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_elimination_missing_checkpoints_rejected(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(checkpoints=[]),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_elimination_missing_operator_rejected(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(elimination_combine_operator=None),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_non_elimination_with_rules_rejected(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json={"mode": "STANDARD", "elimination_rules": [{"type": "FIRST_WRONG"}]},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_n_wrong_defaults_to_three(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(
            elimination_rules=[{"type": "N_WRONG"}],
            checkpoints=[{"type": "AFTER_GROUP"}],
        ),
    )
    assert resp.status_code == 200, resp.text
    rule = resp.json()["elimination_rules"][0]
    assert rule["type"] == "N_WRONG"
    assert rule["n_value"] == 3


@pytest.mark.asyncio
async def test_bottom_percent_out_of_range_rejected(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(
            elimination_rules=[{"type": "BOTTOM_X_PERCENT", "percent_value": 150}],
            checkpoints=[{"type": "AFTER_GROUP"}],
        ),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_after_question_requires_sequence(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json=_elimination_cfg(
            elimination_rules=[{"type": "FIRST_WRONG"}],
            checkpoints=[{"type": "AFTER_QUESTION"}],
        ),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_patch_replaces_rules_and_checkpoints(api):
    oa, contest = await _elimination_contest(api)
    resp = await api.put(
        f"/contests/{contest['id']}/configuration", headers=_auth(oa), json=_elimination_cfg()
    )
    assert resp.status_code == 200, resp.text

    patch = await api.patch(
        f"/contests/{contest['id']}/configuration",
        headers=_auth(oa),
        json={
            "elimination_rules": [{"type": "MIN_SCORE", "min_score": 50}],
            "checkpoints": [{"type": "AFTER_GROUP"}],
        },
    )
    assert patch.status_code == 200, patch.text
    data = patch.json()
    assert [r["type"] for r in data["elimination_rules"]] == ["MIN_SCORE"]
    assert data["elimination_rules"][0]["min_score"] == 50
    assert [c["type"] for c in data["checkpoints"]] == ["AFTER_GROUP"]
