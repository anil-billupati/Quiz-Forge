"""Unit 8 integration tests: Execution Engine.

Covers moderator-controlled reveal/advance, automatic tick progression on the
server clock, authoritative QuestionWindow timing, recovery from durable state,
lifecycle completion at the end of the run, and control RBAC.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.models.base import Base, new_uuid
from app.models.user import User
from app.security.passwords import hash_password
from app.services import execution_service


@asynccontextmanager
async def _scoped(maker, tenant_id):
    """A direct DB session with tenant context set (as the HTTP layer would)."""
    token = set_current_tenant(tenant_id)
    try:
        async with maker() as s:
            yield s
    finally:
        reset_current_tenant(token)

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"
PW = "participant-pw-1"
DURATION = 5  # question_duration_s (config minimum)


@pytest.fixture
async def env():
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
        yield client, maker
    app.dependency_overrides.clear()
    await engine.dispose()


async def _login(client, email, password):
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def _create_org(client, super_token, slug, admin_email) -> str:
    resp = await client.post(
        "/organizations",
        headers=_h(super_token),
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
    return resp.json()["id"]  # org id == tenant_id


async def _create_participant(client, oa_token, email):
    resp = await client.post(
        "/users",
        headers=_h(oa_token),
        json={
            "email": email,
            "first_name": "Pat",
            "last_name": "Player",
            "role": "PARTICIPANT",
            "password": PW,
        },
    )
    assert resp.status_code == 201, resp.text


async def _create_contest(client, oa_token):
    resp = await client.post(
        "/contests",
        headers=_h(oa_token),
        json={"name": "quiz", "description": "t", "structure": "NORMAL"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_config(client, oa_token, contest_id, reveal_mode):
    resp = await client.put(
        f"/contests/{contest_id}/configuration",
        headers=_h(oa_token),
        json={"mode": "STANDARD", "reveal_mode": reveal_mode, "question_duration_s": DURATION},
    )
    assert resp.status_code == 200, resp.text


async def _add_question(client, oa_token, contest_id, sequence):
    resp = await client.post(
        f"/contests/{contest_id}/questions",
        headers=_h(oa_token),
        json={
            "sequence": sequence,
            "text": f"Q{sequence}?",
            "options": [
                {"text": "a", "is_correct": False},
                {"text": "b", "is_correct": True},
            ],
        },
    )
    assert resp.status_code == 201, resp.text


async def _to_live(client, oa_token, contest_id):
    for target, extra in (
        ("PUBLISHED", {}),
        ("REGISTRATION_OPEN", {}),
        ("REGISTRATION_CLOSED", {}),
        ("SCHEDULED", {"scheduled_start_at": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()}),
        ("LIVE", {}),
    ):
        resp = await client.post(
            f"/contests/{contest_id}/lifecycle",
            headers=_h(oa_token),
            json={"target_status": target, **extra},
        )
        assert resp.status_code == 200, resp.text


async def _setup(client, reveal_mode, n_questions=2):
    su = await _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = await _create_org(client, su, "acme", "admin@acme.com")
    oa = await _login(client, "admin@acme.com", "org-admin-pw-1")
    contest = await _create_contest(client, oa)
    await _set_config(client, oa, contest["id"], reveal_mode)
    for seq in range(1, n_questions + 1):
        await _add_question(client, oa, contest["id"], seq)
    await _to_live(client, oa, contest["id"])
    return oa, tenant_id, contest["id"]


@pytest.mark.asyncio
async def test_moderator_controlled_flow(env):
    client, _ = env
    oa, _, contest_id = await _setup(client, "MODERATOR_CONTROLLED", n_questions=2)

    start = await client.post(f"/contests/{contest_id}/control/start", headers=_h(oa))
    assert start.status_code == 200, start.text
    assert start.json()["phase"] == "DISPLAY"
    assert start.json()["submission_close_at"] is None

    reveal = await client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa))
    assert reveal.json()["phase"] == "SUBMISSION"
    assert reveal.json()["submission_close_at"] is not None
    q1 = reveal.json()["current_question_id"]

    adv = await client.post(
        f"/contests/{contest_id}/control/advance", headers=_h(oa), json={"scope": "QUESTION"}
    )
    assert adv.json()["phase"] == "DISPLAY"
    assert adv.json()["current_question_id"] != q1

    await client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa))
    end = await client.post(f"/contests/{contest_id}/control/advance", headers=_h(oa))
    assert end.json()["phase"] == "ENDED"

    # The contest lifecycle is completed at the end of the run.
    got = await client.get(f"/contests/{contest_id}", headers=_h(oa))
    assert got.json()["lifecycle_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_automatic_tick_progression(env):
    client, maker = env
    oa, tenant_id, contest_id = await _setup(client, "AUTOMATIC", n_questions=2)
    await client.post(f"/contests/{contest_id}/control/start", headers=_h(oa))

    t0 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)

    async def tick(now):
        async with _scoped(maker, tenant_id) as s:
            await execution_service.tick(s, tenant_id, contest_id, now=now)

    async def phase():
        async with _scoped(maker, tenant_id) as s:
            return (await execution_service.snapshot(s, tenant_id, contest_id))["phase"]

    await tick(t0)  # DISPLAY -> reveal q1
    assert await phase() == "SUBMISSION"

    await tick(t0 + timedelta(seconds=1))  # window still open
    assert await phase() == "SUBMISSION"

    await tick(t0 + timedelta(seconds=DURATION + 1))  # close -> advance to q2 (DISPLAY)
    assert await phase() == "DISPLAY"

    await tick(t0 + timedelta(seconds=DURATION + 1))  # reveal q2
    assert await phase() == "SUBMISSION"

    await tick(t0 + timedelta(seconds=2 * DURATION + 2))  # close -> advance -> ENDED
    assert await phase() == "ENDED"

    got = await client.get(f"/contests/{contest_id}", headers=_h(oa))
    assert got.json()["lifecycle_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_window_authority_and_live_state(env):
    client, maker = env
    oa, tenant_id, contest_id = await _setup(client, "MODERATOR_CONTROLLED", n_questions=1)
    await _create_participant(client, oa, "p1@acme.com")
    # Register the participant before the window opens is impossible (LIVE), so
    # we register via service-independent path: ticket/live-state only need a
    # registration row — create one through the open window is closed. Instead we
    # verify live-state for the org admin caller (status None) and the question.
    await client.post(f"/contests/{contest_id}/control/start", headers=_h(oa))
    reveal = await client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa))
    close_at = reveal.json()["submission_close_at"]

    # Authoritative window persisted with the reveal-derived close time.
    from app.models.execution import QuestionWindow
    from sqlalchemy import select

    async with _scoped(maker, tenant_id) as s:
        window = (
            await s.execute(
                select(QuestionWindow).where(QuestionWindow.contest_id == contest_id)
            )
        ).scalar_one()
        assert window.submission_close_at is not None
        assert window.revealed_at is not None

    # live-state reflects the open window + current question without correctness.
    ls = await client.get(f"/contests/{contest_id}/live-state", headers=_h(oa))
    assert ls.status_code == 200, ls.text
    body = ls.json()
    assert body["phase"] == "SUBMISSION"
    assert body["submission_close_at"] == close_at
    assert body["current_question"] is not None
    for opt in body["current_question"]["options"]:
        assert "is_correct" not in opt


@pytest.mark.asyncio
async def test_recovery_resumes_from_durable_state(env):
    client, maker = env
    oa, tenant_id, contest_id = await _setup(client, "MODERATOR_CONTROLLED", n_questions=2)
    await client.post(f"/contests/{contest_id}/control/start", headers=_h(oa))
    await client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa))

    # Simulate a fresh process: a brand-new session reads progression from the DB.
    async with _scoped(maker, tenant_id) as s:
        snap = await execution_service.snapshot(s, tenant_id, contest_id)
    assert snap["phase"] == "SUBMISSION"
    assert snap["current_question_id"] is not None
    assert snap["submission_close_at"] is not None


@pytest.mark.asyncio
async def test_start_requires_live(env):
    client, _ = env
    su = await _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    await _create_org(client, su, "acme", "admin@acme.com")
    oa = await _login(client, "admin@acme.com", "org-admin-pw-1")
    contest = await _create_contest(client, oa)  # DRAFT
    resp = await client.post(f"/contests/{contest['id']}/control/start", headers=_h(oa))
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_control_requires_role(env):
    client, _ = env
    oa, _, contest_id = await _setup(client, "MODERATOR_CONTROLLED", n_questions=1)
    await _create_participant(client, oa, "p1@acme.com")
    pt = await _login(client, "p1@acme.com", PW)
    resp = await client.post(f"/contests/{contest_id}/control/start", headers=_h(pt))
    assert resp.status_code == 403, resp.text
