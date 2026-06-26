"""Unit 7 integration tests: real-time gateway (WebSocket + live runtime).

Covers connection tickets, WS handshake auth (valid/invalid/single-use),
heartbeat, connection.ready, local fan-out, and the /live-state snapshot
(409 when not Live). Uses the sync Starlette TestClient because httpx's
ASGITransport does not support WebSockets.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependencies import db_session
from app.main import app
from app.models.base import Base, new_uuid
from app.models.user import User
from app.realtime.gateway import manager, publish_event
from app.security.passwords import hash_password

SUPER_EMAIL = "root@platform.com"
SUPER_PASSWORD = "super-strong-pw"
PW = "participant-pw-1"


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
        yield c
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


def _transition(client, oa_token, contest_id, target, scheduled_start_at=None):
    body = {"target_status": target}
    if scheduled_start_at is not None:
        body["scheduled_start_at"] = scheduled_start_at
    resp = client.post(
        f"/contests/{contest_id}/lifecycle", headers=_h(oa_token), json=body
    )
    assert resp.status_code == 200, resp.text


def _registered_participant(client):
    """Set up acme + a registered participant on a REGISTRATION_OPEN contest.

    Returns (oa_token, participant_token, contest).
    """
    su = _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    _create_org(client, su, "acme", "admin@acme.com")
    oa = _login(client, "admin@acme.com", "org-admin-pw-1")
    _create_participant(client, oa, "p1@acme.com")
    pt = _login(client, "p1@acme.com", PW)
    contest = _create_contest(client, oa)
    _transition(client, oa, contest["id"], "PUBLISHED")
    _transition(client, oa, contest["id"], "REGISTRATION_OPEN")
    reg = client.post(f"/contests/{contest['id']}/registrations", headers=_h(pt))
    assert reg.status_code == 201, reg.text
    return oa, pt, contest


def _ticket(client, token, contest_id):
    resp = client.post(f"/contests/{contest_id}/live-ticket", headers=_h(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["ticket"]


def test_connect_with_valid_ticket_receives_ready(client):
    _, pt, contest = _registered_participant(client)
    ticket = _ticket(client, pt, contest["id"])
    with client.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ready = ws.receive_json()
        assert ready == {"event": "connection.ready", "contest_id": contest["id"]}


def test_heartbeat_ping_pong(client):
    _, pt, contest = _registered_participant(client)
    ticket = _ticket(client, pt, contest["id"])
    with client.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()  # connection.ready
        ws.send_json({"action": "ping"})
        assert ws.receive_json() == {"event": "pong"}


def test_unsupported_action(client):
    _, pt, contest = _registered_participant(client)
    ticket = _ticket(client, pt, contest["id"])
    with client.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "not_a_real_action"})
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["reason"] == "unsupported_action"


def test_connect_without_ticket_rejected(client):
    _, pt, contest = _registered_participant(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/contests/{contest['id']}/live"):
            pass


def test_ticket_is_single_use(client):
    _, pt, contest = _registered_participant(client)
    ticket = _ticket(client, pt, contest["id"])
    with client.websocket_connect(
        f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
    ) as ws:
        ws.receive_json()
    # Same ticket cannot be reused.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/contests/{contest['id']}/live", subprotocols=[f"ticket.{ticket}"]
        ):
            pass


def test_ticket_bound_to_contest(client):
    oa, pt, contest = _registered_participant(client)
    other = _create_contest(client, oa)  # a different contest, same tenant
    ticket = _ticket(client, pt, contest["id"])
    # Ticket for `contest` cannot open `other`'s channel.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/contests/{other['id']}/live", subprotocols=[f"ticket.{ticket}"]
        ):
            pass


def test_unregistered_participant_cannot_get_ticket(client):
    su = _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    _create_org(client, su, "acme", "admin@acme.com")
    oa = _login(client, "admin@acme.com", "org-admin-pw-1")
    _create_participant(client, oa, "p1@acme.com")
    pt = _login(client, "p1@acme.com", PW)
    contest = _create_contest(client, oa)
    _transition(client, oa, contest["id"], "PUBLISHED")
    _transition(client, oa, contest["id"], "REGISTRATION_OPEN")
    # Participant never registered.
    resp = client.post(f"/contests/{contest['id']}/live-ticket", headers=_h(pt))
    assert resp.status_code == 403, resp.text


def test_cross_tenant_ticket_rejected(client):
    su = _login(client, SUPER_EMAIL, SUPER_PASSWORD)
    _create_org(client, su, "acme", "admin@acme.com")
    _create_org(client, su, "globex", "admin@globex.com")
    oa_acme = _login(client, "admin@acme.com", "org-admin-pw-1")
    contest = _create_contest(client, oa_acme)
    oa_globex = _login(client, "admin@globex.com", "org-admin-pw-1")
    # Other tenant cannot mint a ticket for this contest (contest not found).
    resp = client.post(f"/contests/{contest['id']}/live-ticket", headers=_h(oa_globex))
    assert resp.status_code == 404, resp.text


def test_live_state_409_until_live_then_snapshot(client):
    oa, pt, contest = _registered_participant(client)

    not_live = client.get(f"/contests/{contest['id']}/live-state", headers=_h(pt))
    assert not_live.status_code == 409, not_live.text

    # Drive the contest to LIVE.
    _transition(client, oa, contest["id"], "REGISTRATION_CLOSED")
    start_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    _transition(client, oa, contest["id"], "SCHEDULED", scheduled_start_at=start_at)
    _transition(client, oa, contest["id"], "LIVE")

    live = client.get(f"/contests/{contest['id']}/live-state", headers=_h(pt))
    assert live.status_code == 200, live.text
    data = live.json()
    assert data["contest_id"] == contest["id"]
    assert data["status"] == "REGISTERED"


class _FakeWebSocket:
    """Minimal stand-in for a Starlette WebSocket that records sent frames."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_local_fanout_delivers_to_connected_sockets():
    contest_id = "contest-fanout"
    ws_a, ws_b = _FakeWebSocket(), _FakeWebSocket()
    await manager.connect(contest_id, ws_a)
    await manager.connect(contest_id, ws_b)
    try:
        assert manager.local_count(contest_id) == 2
        await publish_event(contest_id, {"event": "contest.progress", "phase": "DISPLAY"})
        expected = {"event": "contest.progress", "phase": "DISPLAY"}
        assert ws_a.sent == [expected]
        assert ws_b.sent == [expected]
    finally:
        manager.disconnect(contest_id, ws_a)
        manager.disconnect(contest_id, ws_b)
    assert manager.local_count(contest_id) == 0
