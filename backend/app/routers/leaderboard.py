"""Leaderboard REST endpoint (api-contracts §Leaderboards).

The live leaderboard is pushed over WebSocket; this endpoint is the REST
fallback / snapshot for reconnection and the moderator console.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardView
from app.services import leaderboard_service as svc

router = APIRouter(tags=["Leaderboards"])
_viewer = require_roles("ORG_ADMIN", "MODERATOR", "PARTICIPANT")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.get("/contests/{contest_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    contest_id: str,
    view: LeaderboardView = Query(default="CONTEST"),
    group_id: str | None = Query(default=None),
    principal: Principal = Depends(_viewer),
    session: AsyncSession = Depends(db_session),
) -> list[LeaderboardEntry]:
    """Return a leaderboard snapshot for the requested view.

    Participants are subject to the contest's ``leaderboard_visibility`` setting.
    Org Admins and Moderators can always retrieve the full board.
    """
    tenant_id = _require_tenant(principal)

    # Resolve the configuration block so we can enforce visibility for participants.
    block = await svc._block_for_view(session, tenant_id, contest_id, view, group_id)
    await svc.check_leaderboard_visibility(
        session, tenant_id, contest_id, block.leaderboard_visibility, principal.role
    )

    entries = await svc.get_leaderboard(session, tenant_id, contest_id, view, group_id)

    if (
        block.leaderboard_visibility == "MASKED"
        and principal.role == "PARTICIPANT"
    ):
        mine = next(
            (e for e in entries if e["participant_id"] == principal.user_id), None
        )
        return [LeaderboardEntry.model_validate(mine)] if mine else []

    return [LeaderboardEntry.model_validate(e) for e in entries]
