"""Auth endpoints (api-contracts Auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, get_principal
from app.middleware.errors import AppError
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: AsyncSession = Depends(db_session)) -> TokenPair:
    tokens = await auth_service.login(session, body.email, body.password)
    return TokenPair(**tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(db_session)) -> TokenPair:
    tokens = await auth_service.refresh(session, body.refresh_token)
    return TokenPair(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, session: AsyncSession = Depends(db_session)) -> Response:
    await auth_service.logout(session, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    user = (
        await session.execute(select(User).where(User.id == principal.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise AppError(404, "NOT_FOUND", "User not found")
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(db_session),
) -> Response:
    await auth_service.change_password(
        session, principal.user_id, body.current_password, body.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
