"""Unit 12 integration tests: Leaderboard Engine.

Covers REST snapshots, rebuild-from-Postgres fallback, visibility modes, and the
WebSocket ``leaderboard.update`` event published on question advance.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.models.base import Base, new_uuid
from app.models.score import Score
from app.models.user import User
from app.security.passwords import hash_password
from app.services import scoring_service

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"
PW = "participant-pw-1"
DURATION = 300


@pytest.fixture
def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create_all():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _seed():
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

    asyncio.run(_create_all())
    asyncio.run(_seed())

    async def _override():
        async with maker() as s:
            yield s

    app.dependency_overrides[db_session] = _override
    with TestClient(app) as c:
        yield c, maker
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


@asynccontextmanager
async def _scoped(maker, tenant_id):
    token = set_current_tenant(tenant_id)
    try:
        async with maker() as s:
            yield s
    finally:
        reset_current_tenant(token)


def _login(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_org(client, super_token, slug, admin_email):
    resp = client.post(
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
    return resp.json()["id"]


def _create_participant(client, oa_token, email):
    resp = client.post(
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


def _create_contest(client, oa_token):
    resp = client.post(
        "/contests",
        headers=_h(oa_token),
        json={"name": "quiz", "description": "t", "structure": "NORMAL"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_config(client, oa_token, contest_id, **overrides):
    body = {
        "mode": "STANDARD",
        "reveal_mode": "MODERATOR_CONTROLLED",
        "question_duration_s": DURATION,
        "ranking_criterion": "SCORE_ONLY",
        "tie_display": "SHARED_RANK",
        "leaderboard_visibility": "ALWAYS",
        "update_frequency": "PER_QUESTION",
    }
    body.update(overrides)
    resp = client.put(
        f"/contests/{contest_id}/configuration", headers=_h(oa_token), json=body
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _add_question(client, oa_token, contest_id, sequence, n_options=4):
    options = [{"text": f"o{i}", "is_correct": i == 1} for i in range(n_options)]
    resp = client.post(
        f"/contests/{contest_id}/questions",
        headers=_h(oa_token),
        json={"sequence": sequence, "text": f"Q{sequence}?", "options": options},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _transition(client, oa_token, contest_id, target, scheduled_start_at=None):
    body = {"target_status": target}
    if scheduled_start_at is not None:
        body["scheduled_start_at"] = scheduled_start_at
    resp = client.post(f"/contests/{contest_id}/lifecycle", headers=_h(oa_token), json=body)
    assert resp.status_code == 200, resp.text


def _register(client, contest_id, participant_token):
    resp = client.post(f"/contests/{contest_id}/registrations", headers=_h(participant_token))
    assert resp.status_code == 201, resp.text


def _go_live(client, oa_token, contest_id):
    _transition(client, oa_token, contest_id, "REGISTRATION_CLOSED")
    start_at = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    _transition(client, oa_token, contest_id, "SCHEDULED", scheduled_start_at=start_at)
    _transition(client, oa_token, contest_id, "LIVE")
    client.post(f"/contests/{contest_id}/control/start", headers=_h(oa_token))
    client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa_token))


def _ticket(client, contest_id, participant_token):
    return client.post(
        f"/contests/{contest_id}/live-ticket", headers=_h(participant_token)
    ).json()["ticket"]


def _submit_answer(client, contest_id, question, participant_token, correct=False, attempt_no=1):
    opts = {o["is_correct"]: o["id"] for o in question["options"]}
    selected = opts[correct]
    ticket = _ticket(client, contest_id, participant_token)
    with client.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()  # connection.ready
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": selected,
                "attempt_no": attempt_no,
            }
        )
        ack = ws.receive_json()
    assert ack["accepted"] is True, ack


# --- REST snapshot -----------------------------------------------------------


def test_leaderboard_rest_snapshot_orders_by_score(client):
    c, maker = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(c, su, "acme", "admin@acme.com")
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p1@acme.com")
    _create_participant(c, oa, "p2@acme.com")
    p1 = _login(c, "p1@acme.com", PW)
    p2 = _login(c, "p2@acme.com", PW)
    contest = _create_contest(c, oa)
    _set_config(c, oa, contest["id"])
    q1 = _add_question(c, oa, contest["id"], 1)
    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _register(c, contest["id"], p1)
    _register(c, contest["id"], p2)
    _go_live(c, oa, contest["id"])

    # p2 answers correctly; p1 answers incorrectly.
    opts = {o["is_correct"]: o["id"] for o in q1["options"]}
    _submit_answer(c, contest["id"], q1, p2, correct=True)
    _submit_answer(c, contest["id"], q1, p1, correct=False)

    async def _score():
        async with _scoped(maker, tenant_id) as s:
            await scoring_service.score_unscored(s, contest["id"])

    asyncio.run(_score())

    # Advance to close the question so PER_QUESTION update pushes and leaderboard is visible.
    c.post(f"/contests/{contest['id']}/control/advance", headers=_h(oa))

    resp = c.get(f"/contests/{contest['id']}/leaderboard", headers=_h(oa))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert body[0]["participant_id"] == _user_id_from_token(c, p2)
    assert body[0]["score"] == 10
    assert body[0]["rank"] == 1
    assert body[1]["participant_id"] == _user_id_from_token(c, p1)
    assert body[1]["score"] == 0
    assert body[1]["rank"] == 2


def _user_id_from_token(client, token):
    resp = client.get("/auth/me", headers=_h(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# --- Visibility modes --------------------------------------------------------


def test_hidden_leaderboard_blocks_participant_but_allows_admin(client):
    c, maker = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(c, su, "acme", "admin@acme.com")
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p1@acme.com")
    p1 = _login(c, "p1@acme.com", PW)
    contest = _create_contest(c, oa)
    _set_config(c, oa, contest["id"], leaderboard_visibility="HIDDEN")
    _add_question(c, oa, contest["id"], 1)
    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _register(c, contest["id"], p1)
    _go_live(c, oa, contest["id"])

    resp = c.get(f"/contests/{contest['id']}/leaderboard", headers=_h(p1))
    assert resp.status_code == 403, resp.text

    resp = c.get(f"/contests/{contest['id']}/leaderboard", headers=_h(oa))
    assert resp.status_code == 200, resp.text


def test_masked_leaderboard_returns_only_self_for_participant(client):
    c, maker = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(c, su, "acme", "admin@acme.com")
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p1@acme.com")
    _create_participant(c, oa, "p2@acme.com")
    p1 = _login(c, "p1@acme.com", PW)
    p2 = _login(c, "p2@acme.com", PW)
    contest = _create_contest(c, oa)
    _set_config(c, oa, contest["id"], leaderboard_visibility="MASKED")
    q1 = _add_question(c, oa, contest["id"], 1)
    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _register(c, contest["id"], p1)
    _register(c, contest["id"], p2)
    _go_live(c, oa, contest["id"])

    _submit_answer(c, contest["id"], q1, p2, correct=True)
    _submit_answer(c, contest["id"], q1, p1, correct=False)

    async def _score():
        async with _scoped(maker, tenant_id) as s:
            await scoring_service.score_unscored(s, contest["id"])

    asyncio.run(_score())
    c.post(f"/contests/{contest['id']}/control/advance", headers=_h(oa))

    p1_id = _user_id_from_token(c, p1)
    resp = c.get(f"/contests/{contest['id']}/leaderboard", headers=_h(p1))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["participant_id"] == p1_id


# --- WebSocket push ------------------------------------------------------------


def test_leaderboard_update_pushed_on_advance(client):
    c, maker = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    _create_org(c, su, "acme", "admin@acme.com")
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p1@acme.com")
    p1 = _login(c, "p1@acme.com", PW)
    contest = _create_contest(c, oa)
    _set_config(c, oa, contest["id"], leaderboard_visibility="ALWAYS")
    q1 = _add_question(c, oa, contest["id"], 1)
    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _register(c, contest["id"], p1)
    _go_live(c, oa, contest["id"])

    ticket = _ticket(c, contest["id"], p1)
    with c.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()  # connection.ready
        _submit_answer(c, contest["id"], q1, p1, correct=True)
        c.post(f"/contests/{contest['id']}/control/advance", headers=_h(oa))
        # advance publishes contest.progress first, then leaderboard.update.
        progress = ws.receive_json()
        assert progress["event"] == "contest.progress"
        msg = ws.receive_json()

    assert msg["event"] == "leaderboard.update"
    assert msg["view"] == "CONTEST"
    assert len(msg["entries"]) == 1
