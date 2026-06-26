"""Unit 9 integration tests: answer submission & durability.

Covers WebSocket answer.submit intake, server-authoritative validation, durable
persistence, idempotency, late-submission rejection, and transactional outbox.
Uses Starlette's sync TestClient for WebSockets and asyncio.run for direct DB
assertions.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.models.answer import AnswerSubmission, OutboxEvent
from app.models.base import Base, new_uuid
from app.models.user import User
from app.security.passwords import hash_password

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"
PW = "participant-pw-1"
DURATION = 5  # short window for late-submission tests


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
    return resp.json()["id"]  # org id == tenant_id


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


def _set_config(client, oa_token, contest_id):
    resp = client.put(
        f"/contests/{contest_id}/configuration",
        headers=_h(oa_token),
        json={
            "mode": "STANDARD",
            "reveal_mode": "MODERATOR_CONTROLLED",
            "question_duration_s": DURATION,
        },
    )
    assert resp.status_code == 200, resp.text


def _add_question(client, oa_token, contest_id, sequence):
    resp = client.post(
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
    return resp.json()


def _transition(client, oa_token, contest_id, target, scheduled_start_at=None):
    body = {"target_status": target}
    if scheduled_start_at is not None:
        body["scheduled_start_at"] = scheduled_start_at
    resp = client.post(
        f"/contests/{contest_id}/lifecycle", headers=_h(oa_token), json=body
    )
    assert resp.status_code == 200, resp.text


def _live_contest_with_participant(client):
    """Set up a LIVE contest with one registered participant and one revealed question.

    Returns (tenant_id, oa_token, participant_token, contest_id, question, option_id).
    """
    su = _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(client, su, "acme", "admin@acme.com")
    oa = _login(client, "admin@acme.com", "org-admin-pw-1")
    _create_participant(client, oa, "p1@acme.com")
    pt = _login(client, "p1@acme.com", PW)
    contest = _create_contest(client, oa)
    _set_config(client, oa, contest["id"])
    question = _add_question(client, oa, contest["id"], 1)

    _transition(client, oa, contest["id"], "PUBLISHED")
    _transition(client, oa, contest["id"], "REGISTRATION_OPEN")
    reg = client.post(f"/contests/{contest['id']}/registrations", headers=_h(pt))
    assert reg.status_code == 201, reg.text
    _transition(client, oa, contest["id"], "REGISTRATION_CLOSED")
    start_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    _transition(client, oa, contest["id"], "SCHEDULED", scheduled_start_at=start_at)
    _transition(client, oa, contest["id"], "LIVE")

    start = client.post(f"/contests/{contest['id']}/control/start", headers=_h(oa))
    assert start.status_code == 200, start.text
    reveal = client.post(f"/contests/{contest['id']}/control/reveal", headers=_h(oa))
    assert reveal.status_code == 200, reveal.text

    correct_option = [o for o in question["options"] if o["is_correct"]][0]
    return tenant_id, oa, pt, contest["id"], question, correct_option["id"]


def _ticket(client, token, contest_id):
    resp = client.post(f"/contests/{contest_id}/live-ticket", headers=_h(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["ticket"]


async def _scoped_count(maker, tenant_id, model, **filters):
    token = set_current_tenant(tenant_id)
    try:
        async with maker() as s:
            result = await s.execute(
                select(func.count()).select_from(model).where(
                    *[getattr(model, k) == v for k, v in filters.items()]
                )
            )
            return result.scalar()
    finally:
        reset_current_tenant(token)


def test_submit_answer_accepted_and_acked(client):
    c, maker = client
    tenant_id, oa, pt, contest_id, question, option_id = _live_contest_with_participant(c)
    ticket = _ticket(c, pt, contest_id)

    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()  # connection.ready
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": option_id,
                "attempt_no": 1,
            }
        )
        ack = ws.receive_json()
        assert ack["event"] == "answer.ack"
        assert ack["accepted"] is True
        assert ack["attempt_no"] == 1
        assert ack["submission_id"] is not None

    async def _assert():
        token = set_current_tenant(tenant_id)
        try:
            async with maker() as s:
                sub = (await s.execute(select(AnswerSubmission))).scalar_one()
                assert sub.contest_id == contest_id
                assert sub.question_id == question["id"]
                assert sub.selected_option_id == option_id
                assert sub.status == "ACCEPTED"
                outbox = (await s.execute(select(OutboxEvent))).scalar_one()
                assert outbox.topic == "answer.submitted"
                assert outbox.payload["answer_submission_id"] == sub.id
                assert outbox.status == "PUBLISHED"
        finally:
            reset_current_tenant(token)

    asyncio.run(_assert())


def test_duplicate_submit_is_idempotent(client):
    c, maker = client
    tenant_id, oa, pt, contest_id, question, option_id = _live_contest_with_participant(c)
    ticket = _ticket(c, pt, contest_id)

    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        payload = {
            "action": "answer.submit",
            "question_id": question["id"],
            "selected_option_id": option_id,
            "attempt_no": 1,
        }
        ws.send_json(payload)
        ack1 = ws.receive_json()
        ws.send_json(payload)
        ack2 = ws.receive_json()
        assert ack1 == ack2
        assert ack1["accepted"] is True

    count = asyncio.run(
        _scoped_count(maker, tenant_id, AnswerSubmission, contest_id=contest_id)
    )
    assert count == 1


def test_late_submit_rejected_window_closed(client):
    c, maker = client
    tenant_id, oa, pt, contest_id, question, option_id = _live_contest_with_participant(c)
    ticket = _ticket(c, pt, contest_id)

    # Connect while the ticket is fresh; freeze time only for the submit.
    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=DURATION + 1)):
            ws.send_json(
                {
                    "action": "answer.submit",
                    "question_id": question["id"],
                    "selected_option_id": option_id,
                    "attempt_no": 1,
                }
            )
            ack = ws.receive_json()
            assert ack["event"] == "answer.ack"
            assert ack["accepted"] is False
            assert ack["reason"] == "window_closed"


def test_submit_requires_registration(client):
    c, _ = client
    su = _login(c, SUPER_EMAIL, SUPER_PASSWORD)
    tenant_id = _create_org(c, su, "acme2", "admin2@acme.com")
    oa = _login(c, "admin2@acme.com", "org-admin-pw-1")
    _create_participant(c, oa, "p2@acme.com")
    contest = _create_contest(c, oa)
    _set_config(c, oa, contest["id"])
    question = _add_question(c, oa, contest["id"], 1)

    _transition(c, oa, contest["id"], "PUBLISHED")
    _transition(c, oa, contest["id"], "REGISTRATION_OPEN")
    _transition(c, oa, contest["id"], "REGISTRATION_CLOSED")
    start_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    _transition(c, oa, contest["id"], "SCHEDULED", scheduled_start_at=start_at)
    _transition(c, oa, contest["id"], "LIVE")
    c.post(f"/contests/{contest['id']}/control/start", headers=_h(oa))
    c.post(f"/contests/{contest['id']}/control/reveal", headers=_h(oa))

    # Connect as Org Admin (no registration) and submit.
    ticket = _ticket(c, oa, contest["id"])
    with c.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": question["options"][0]["id"],
                "attempt_no": 1,
            }
        )
        ack = ws.receive_json()
        assert ack["event"] == "answer.ack"
        assert ack["accepted"] is False
        assert ack["reason"] == "not_registered"


def test_submit_wrong_question(client):
    c, _ = client
    tenant_id, oa, pt, contest_id, question, option_id = _live_contest_with_participant(c)
    ticket = _ticket(c, pt, contest_id)

    with c.websocket_connect(
        f"/contests/{contest_id}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": "00000000-0000-0000-0000-000000000000",
                "selected_option_id": option_id,
                "attempt_no": 1,
            }
        )
        ack = ws.receive_json()
        assert ack["event"] == "answer.ack"
        assert ack["accepted"] is False
        assert ack["reason"] == "wrong_question"
