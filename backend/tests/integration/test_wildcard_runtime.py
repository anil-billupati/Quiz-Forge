"""Unit 11 integration tests: Wildcard runtime.

Exercises the WS ``wildcard.activate`` flow end-to-end for each wildcard:
Fifty-Fifty (option removal + double-tap idempotency + post-answer rejection +
not-enabled rejection), Skip (durable SKIPPED answer scored full value), Second
Chance (unlocks attempt 2; blocked without activation), and TOP_50_PERCENT
eligibility rejection. Mirrors test_scoring_engine.py's harness.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.models.answer import AnswerSubmission
from app.models.base import Base, new_uuid
from app.models.score import Score
from app.models.user import User
from app.models.wildcard_activation import WildcardActivation
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


def _set_config(client, oa_token, contest_id, mode="STANDARD"):
    body = {"mode": mode, "reveal_mode": "MODERATOR_CONTROLLED", "question_duration_s": DURATION}
    resp = client.put(
        f"/contests/{contest_id}/configuration", headers=_h(oa_token), json=body
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _enable_wildcard(client, oa_token, block_id, wtype, eligibility="ALL"):
    resp = client.post(
        f"/configuration-blocks/{block_id}/wildcards",
        headers=_h(oa_token),
        json={"type": wtype, "eligibility": eligibility},
    )
    assert resp.status_code == 201, resp.text


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
    start_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    _transition(client, oa_token, contest_id, "SCHEDULED", scheduled_start_at=start_at)
    _transition(client, oa_token, contest_id, "LIVE")
    client.post(f"/contests/{contest_id}/control/start", headers=_h(oa_token))
    client.post(f"/contests/{contest_id}/control/reveal", headers=_h(oa_token))


def _ticket(client, contest_id, participant_token):
    return client.post(
        f"/contests/{contest_id}/live-ticket", headers=_h(participant_token)
    ).json()["ticket"]


def _setup(client, wildcards, mode="STANDARD", n_options=4):
    """One participant, LIVE contest with a revealed question and the given
    wildcards enabled. Returns (tenant_id, contest_id, question, participant_token)."""
    su = _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(client, su, "acme", "admin@acme.com")
    oa = _login(client, "admin@acme.com", "org-admin-pw-1")
    _create_participant(client, oa, "p1@acme.com")
    pt = _login(client, "p1@acme.com", PW)
    contest = _create_contest(client, oa)
    block = _set_config(client, oa, contest["id"], mode=mode)
    for wtype, elig in wildcards:
        _enable_wildcard(client, oa, block["id"], wtype, elig)
    question = _add_question(client, oa, contest["id"], 1, n_options=n_options)
    _transition(client, oa, contest["id"], "PUBLISHED")
    _transition(client, oa, contest["id"], "REGISTRATION_OPEN")
    _register(client, contest["id"], pt)
    _go_live(client, oa, contest["id"])
    return tenant_id, contest["id"], question, pt


# --- Fifty-Fifty -----------------------------------------------------------


def test_fifty_fifty_removes_two_options(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [("FIFTY_FIFTY", "ALL")])
    correct = [o for o in question["options"] if o["is_correct"]][0]
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        result = ws.receive_json()
    assert result["event"] == "wildcard.applied"
    assert result["accepted"] is True
    removed = result["outcome"]["removed_options"]
    assert len(removed) == 2
    assert correct["id"] not in removed


def test_fifty_fifty_double_tap_is_idempotent(client):
    c, maker = client
    tenant_id, contest_id, question, pt = _setup(c, [("FIFTY_FIFTY", "ALL")])
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        first = ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        second = ws.receive_json()
    assert first["accepted"] is True and second["accepted"] is True
    assert first["activation_id"] == second["activation_id"]

    async def _count():
        async with _scoped(maker, tenant_id) as s:
            rows = (
                await s.execute(
                    select(WildcardActivation).where(
                        WildcardActivation.contest_id == contest_id
                    )
                )
            ).scalars().all()
            assert len(rows) == 1

    asyncio.run(_count())


def test_fifty_fifty_rejected_after_answer_selected(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [("FIFTY_FIFTY", "ALL")])
    correct = [o for o in question["options"] if o["is_correct"]][0]
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": correct["id"],
                "attempt_no": 1,
            }
        )
        assert ws.receive_json()["accepted"] is True
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        result = ws.receive_json()
    assert result["accepted"] is False
    assert result["reason"] == "answer_already_selected"


def test_wildcard_not_enabled_is_rejected(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [])  # nothing enabled
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        result = ws.receive_json()
    assert result["accepted"] is False
    assert result["reason"] == "wildcard_not_enabled"


# --- Skip ------------------------------------------------------------------


def test_skip_records_skipped_answer_scored_full(client):
    c, maker = client
    tenant_id, contest_id, question, pt = _setup(c, [("SKIP", "ALL")])
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "wildcard.activate", "type": "SKIP", "question_id": question["id"]})
        result = ws.receive_json()
    assert result["accepted"] is True
    assert result["outcome"]["skipped"] is True

    async def _check():
        async with _scoped(maker, tenant_id) as s:
            sub = (
                await s.execute(
                    select(AnswerSubmission).where(
                        AnswerSubmission.contest_id == contest_id
                    )
                )
            ).scalar_one()
            assert sub.outcome == "SKIPPED"
            assert sub.selected_option_id is None
            scored = await scoring_service.score_unscored(s, contest_id)
            assert scored == 1
            score = (
                await s.execute(select(Score).where(Score.contest_id == contest_id))
            ).scalar_one()
            assert score.points == 10  # FR-25: full correct value under Fixed

    asyncio.run(_check())


# --- Second Chance ---------------------------------------------------------


def test_second_chance_unlocks_attempt_two(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [("SECOND_CHANCE", "ALL")])
    opts = {o["is_correct"]: o["id"] for o in question["options"]}
    wrong_id, correct_id = opts[False], opts[True]
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        # First attempt wrong.
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": wrong_id,
                "attempt_no": 1,
            }
        )
        assert ws.receive_json()["accepted"] is True
        # Activate Second Chance.
        ws.send_json(
            {"action": "wildcard.activate", "type": "SECOND_CHANCE", "question_id": question["id"]}
        )
        assert ws.receive_json()["accepted"] is True
        # Second attempt now allowed.
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": correct_id,
                "attempt_no": 2,
            }
        )
        ack2 = ws.receive_json()
    assert ack2["accepted"] is True
    assert ack2["attempt_no"] == 2


def test_attempt_two_without_second_chance_rejected(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [("SECOND_CHANCE", "ALL")])
    opts = {o["is_correct"]: o["id"] for o in question["options"]}
    wrong_id, correct_id = opts[False], opts[True]
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": wrong_id,
                "attempt_no": 1,
            }
        )
        assert ws.receive_json()["accepted"] is True
        # Skip the wildcard; attempt 2 must be rejected.
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": correct_id,
                "attempt_no": 2,
            }
        )
        ack2 = ws.receive_json()
    assert ack2["accepted"] is False
    assert ack2["reason"] == "conflict_no_second_chance"


# --- Audit -----------------------------------------------------------------


def test_wildcard_audit_lists_activations(client):
    c, _ = client
    _, contest_id, question, pt = _setup(c, [("FIFTY_FIFTY", "ALL")])
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    ticket = _ticket(c, contest_id, pt)
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": question["id"]}
        )
        assert ws.receive_json()["accepted"] is True

    resp = c.get(f"/contests/{contest_id}/wildcard-audit", headers=_h(oa))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["type"] == "FIFTY_FIFTY"
    assert body[0]["question_id"] == question["id"]
    assert "removed_options" in body[0]["outcome"]


# --- Eligibility -----------------------------------------------------------


def test_top_50_percent_excludes_bottom_participant(client):
    c, maker = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(c, su, "acme", "admin@acme.com")
    oa = _login(c, "admin@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p1@acme.com")
    _create_participant(c, oa, "p2@acme.com")
    p1 = _login(c, "p1@acme.com", PW)
    p2 = _login(c, "p2@acme.com", PW)
    contest = _create_contest(c, oa)
    block = _set_config(c, oa, contest["id"])
    _enable_wildcard(c, oa, block["id"], "FIFTY_FIFTY", "TOP_50_PERCENT")
    q1 = _add_question(c, oa, contest["id"], 1)
    q2 = _add_question(c, oa, contest["id"], 2)
    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _register(c, contest["id"], p1)
    _register(c, contest["id"], p2)
    _go_live(c, oa, contest["id"])

    # p1 answers Q1 correctly so the committed board has p1 above p2.
    correct1 = [o for o in q1["options"] if o["is_correct"]][0]
    t1 = _ticket(c, contest["id"], p1)
    with c.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{t1}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": q1["id"],
                "selected_option_id": correct1["id"],
                "attempt_no": 1,
            }
        )
        assert ws.receive_json()["accepted"] is True

    async def _score():
        async with _scoped(maker, tenant_id) as s:
            await scoring_service.score_unscored(s, contest["id"])

    asyncio.run(_score())

    # Advance to Q2 so a window is open for the wildcard.
    c.post(f"/contests/{contest['id']}/control/advance", headers=_h(oa))
    c.post(f"/contests/{contest['id']}/control/reveal", headers=_h(oa))

    # p2 (bottom of the board) is not eligible; p1 (top) is.
    t2 = _ticket(c, contest["id"], p2)
    with c.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{t2}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": q2["id"]}
        )
        rejected = ws.receive_json()
    assert rejected["accepted"] is False
    assert rejected["reason"] == "wildcard_not_eligible"

    t1b = _ticket(c, contest["id"], p1)
    with c.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{t1b}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {"action": "wildcard.activate", "type": "FIFTY_FIFTY", "question_id": q2["id"]}
        )
        accepted = ws.receive_json()
    assert accepted["accepted"] is True
