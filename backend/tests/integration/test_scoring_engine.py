"""Unit 10 integration tests: Scoring Engine.

End-to-end submit -> score, at-most-once idempotency, and recovery re-drive of
unscored answers. Uses in-memory SQLite with the db_session override and a direct
tenant-scoped session for service calls and assertions (mirrors
test_answer_submission.py / test_execution_engine.py).
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
from app.security.passwords import hash_password
from app.services import scoring_service

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"
PW = "participant-pw-1"
DURATION = 300  # long window so setup time never closes it


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


def _live_with_answer(client, correct=True):
    """LIVE contest, revealed question, one submitted answer. Returns context."""
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
    client.post(f"/contests/{contest['id']}/control/start", headers=_h(oa))
    client.post(f"/contests/{contest['id']}/control/reveal", headers=_h(oa))

    option = [o for o in question["options"] if o["is_correct"] == correct][0]
    ticket = client.post(
        f"/contests/{contest['id']}/live-ticket", headers=_h(pt)
    ).json()["ticket"]
    with client.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "answer.submit",
                "question_id": question["id"],
                "selected_option_id": option["id"],
                "attempt_no": 1,
            }
        )
        ack = ws.receive_json()
        assert ack["accepted"] is True, ack
        submission_id = ack["submission_id"]
    return tenant_id, contest["id"], submission_id


def test_score_answer_creates_score(client):
    c, maker = client
    tenant_id, contest_id, submission_id = _live_with_answer(c, correct=True)

    async def _run():
        async with _scoped(maker, tenant_id) as s:
            score = await scoring_service.score_answer(s, submission_id)
            assert score is not None
            assert score.points == 10  # default correct_points, FIXED
            assert score.scoring_model == "FIXED"
            assert score.answer_submission_id == submission_id
            sub = (
                await s.execute(
                    select(AnswerSubmission).where(AnswerSubmission.id == submission_id)
                )
            ).scalar_one()
            assert sub.scored is True
            assert sub.outcome == "CORRECT"

    asyncio.run(_run())


def test_wrong_answer_scores_zero(client):
    c, maker = client
    tenant_id, contest_id, submission_id = _live_with_answer(c, correct=False)

    async def _run():
        async with _scoped(maker, tenant_id) as s:
            score = await scoring_service.score_answer(s, submission_id)
            assert score is not None
            assert score.points == 0

    asyncio.run(_run())


def test_score_answer_is_idempotent(client):
    c, maker = client
    tenant_id, contest_id, submission_id = _live_with_answer(c, correct=True)

    async def _run():
        async with _scoped(maker, tenant_id) as s:
            first = await scoring_service.score_answer(s, submission_id)
            second = await scoring_service.score_answer(s, submission_id)
            assert first.id == second.id
            count = len(
                (
                    await s.execute(
                        select(Score).where(Score.answer_submission_id == submission_id)
                    )
                ).scalars().all()
            )
            assert count == 1

    asyncio.run(_run())


def test_score_unscored_redrive(client):
    c, maker = client
    tenant_id, contest_id, submission_id = _live_with_answer(c, correct=True)

    async def _run():
        async with _scoped(maker, tenant_id) as s:
            # Nothing scored yet (Redis publish is a no-op in tests).
            scored = await scoring_service.score_unscored(s, contest_id)
            assert scored == 1
            # Re-driving again scores nothing new (idempotent).
            again = await scoring_service.score_unscored(s, contest_id)
            assert again == 0

    asyncio.run(_run())
