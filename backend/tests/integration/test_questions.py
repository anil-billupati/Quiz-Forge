"""Unit 5 integration tests: Question & Option authoring.

Validates CRUD, ≥2 options / exactly one correct (BR-21), group-scope rules,
sequence uniqueness, Draft-only editing, and tenant isolation.
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


async def _create_contest(client, oa, structure="NORMAL", name="quiz") -> dict:
    resp = await client.post(
        "/contests",
        headers=_auth(oa),
        json={"name": name, "description": "test", "structure": structure},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_group(client, oa, contest_id, sequence=1) -> dict:
    resp = await client.post(
        f"/contests/{contest_id}/groups",
        headers=_auth(oa),
        json={"name": f"Group {sequence}", "sequence": sequence, "weight": None},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _acme_admin(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    return await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")


def _question(**overrides) -> dict:
    q = {
        "sequence": 1,
        "text": "What is 2+2?",
        "explanation": "Basic arithmetic.",
        "options": [
            {"text": "3", "is_correct": False},
            {"text": "4", "is_correct": True},
        ],
    }
    q.update(overrides)
    return q


@pytest.mark.asyncio
async def test_create_list_and_get_question(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)

    resp = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question()
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["text"] == "What is 2+2?"
    assert len(data["options"]) == 2
    # Admin view includes correctness and ordinals.
    assert [o["ordinal"] for o in data["options"]] == [0, 1]
    assert data["options"][1]["is_correct"] is True
    qid = data["id"]

    lst = await api.get(f"/contests/{contest['id']}/questions", headers=_auth(oa))
    assert lst.status_code == 200
    assert len(lst.json()) == 1

    one = await api.get(
        f"/contests/{contest['id']}/questions/{qid}", headers=_auth(oa)
    )
    assert one.status_code == 200
    assert one.json()["id"] == qid


@pytest.mark.asyncio
async def test_exactly_one_correct_required(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)

    two_correct = _question(
        options=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]
    )
    resp = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=two_correct
    )
    assert resp.status_code == 422, resp.text

    none_correct = _question(
        options=[{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]
    )
    resp = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=none_correct
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_min_two_options_required(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    resp = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(options=[{"text": "only", "is_correct": True}]),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_normal_contest_rejects_group_id(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    resp = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(group_id="some-group"),
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_grouped_contest_requires_valid_group(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa, structure="GROUPED")
    group = await _create_group(api, oa, contest["id"])

    # Missing group_id → 422.
    resp = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question()
    )
    assert resp.status_code == 422, resp.text

    # Valid group → 201, and ?group_id filter returns it.
    resp = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(group_id=group["id"]),
    )
    assert resp.status_code == 201, resp.text

    lst = await api.get(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        params={"group_id": group["id"]},
    )
    assert lst.status_code == 200
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_sequence_rejected_in_contest(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    first = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question(sequence=1)
    )
    assert first.status_code == 201
    dup = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(sequence=1, text="another"),
    )
    assert dup.status_code == 409, dup.text


@pytest.mark.asyncio
async def test_same_sequence_allowed_across_groups(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa, structure="GROUPED")
    g1 = await _create_group(api, oa, contest["id"], sequence=1)
    g2 = await _create_group(api, oa, contest["id"], sequence=2)

    r1 = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(sequence=1, group_id=g1["id"]),
    )
    assert r1.status_code == 201, r1.text
    r2 = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(sequence=1, group_id=g2["id"]),
    )
    assert r2.status_code == 201, r2.text


@pytest.mark.asyncio
async def test_patch_and_replace_options(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    created = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question()
    )
    qid = created.json()["id"]

    patch = await api.patch(
        f"/contests/{contest['id']}/questions/{qid}",
        headers=_auth(oa),
        json={"text": "Updated?", "sequence": 5},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["text"] == "Updated?"
    assert patch.json()["sequence"] == 5

    replace = await api.put(
        f"/contests/{contest['id']}/questions/{qid}/options",
        headers=_auth(oa),
        json={
            "options": [
                {"text": "x", "is_correct": False},
                {"text": "y", "is_correct": False},
                {"text": "z", "is_correct": True},
            ]
        },
    )
    assert replace.status_code == 200, replace.text
    opts = replace.json()["options"]
    assert len(opts) == 3
    assert [o["ordinal"] for o in opts] == [0, 1, 2]
    assert opts[2]["is_correct"] is True


@pytest.mark.asyncio
async def test_delete_question(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    created = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question()
    )
    qid = created.json()["id"]
    delete = await api.delete(
        f"/contests/{contest['id']}/questions/{qid}", headers=_auth(oa)
    )
    assert delete.status_code == 204
    gone = await api.get(
        f"/contests/{contest['id']}/questions/{qid}", headers=_auth(oa)
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_questions_locked_after_publish(api):
    oa = await _acme_admin(api)
    contest = await _create_contest(api, oa)
    created = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa), json=_question()
    )
    assert created.status_code == 201

    pub = await api.post(
        f"/contests/{contest['id']}/lifecycle",
        headers=_auth(oa),
        json={"target_status": "PUBLISHED"},
    )
    assert pub.status_code == 200

    resp = await api.post(
        f"/contests/{contest['id']}/questions",
        headers=_auth(oa),
        json=_question(sequence=2),
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_cross_tenant_question_isolation(api):
    su = await _login(api, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(api, su, "acme", "admin@acme.com")
    await _create_org(api, su, "globex", "admin@globex.com")

    oa_acme = await _login(api, "admin@acme.com", "org-admin-pw-1", tenant_slug="acme")
    contest = await _create_contest(api, oa_acme)
    created = await api.post(
        f"/contests/{contest['id']}/questions", headers=_auth(oa_acme), json=_question()
    )
    qid = created.json()["id"]

    oa_globex = await _login(api, "admin@globex.com", "org-admin-pw-1", tenant_slug="globex")
    resp = await api.get(
        f"/contests/{contest['id']}/questions/{qid}", headers=_auth(oa_globex)
    )
    assert resp.status_code == 404
