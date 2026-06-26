"""Operational CLI.

Super Admin bootstrap (technical-spec §4): the first Super Admin is seeded
outside the tenant API. Run once after migrations:

    CF_BOOTSTRAP_SUPERADMIN_EMAIL=admin@platform.test \\
    CF_BOOTSTRAP_SUPERADMIN_PASSWORD=change-me-strong \\
    python -m app.cli seed-superadmin

Idempotent: does nothing if a Super Admin with that email already exists.
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.base import new_uuid
from app.models.user import User
from app.security.passwords import hash_password
from app.services import answer_service


async def _seed_super_admin(email: str, password: str, first: str, last: str) -> str:
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(User).where(User.email == email, User.tenant_id.is_(None))
            )
        ).scalar_one_or_none()
        if existing is not None:
            return f"Super Admin {email} already exists ({existing.id}); no action."
        user = User(
            id=new_uuid(),
            tenant_id=None,
            email=email,
            password_hash=hash_password(password),
            role="SUPER_ADMIN",
            first_name=first,
            last_name=last,
        )
        session.add(user)
        await session.commit()
        return f"Created Super Admin {email} ({user.id})."


def seed_superadmin() -> None:
    email = os.environ.get("CF_BOOTSTRAP_SUPERADMIN_EMAIL")
    password = os.environ.get("CF_BOOTSTRAP_SUPERADMIN_PASSWORD")
    if not email or not password:
        print(
            "Set CF_BOOTSTRAP_SUPERADMIN_EMAIL and CF_BOOTSTRAP_SUPERADMIN_PASSWORD.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    first = os.environ.get("CF_BOOTSTRAP_SUPERADMIN_FIRST_NAME", "Super")
    last = os.environ.get("CF_BOOTSTRAP_SUPERADMIN_LAST_NAME", "Admin")
    print(asyncio.run(_seed_super_admin(email, password, first, last)))


async def _redrive_outbox() -> int:
    async with SessionLocal() as session:
        return await answer_service.redrive_pending_outbox(session)


def redrive_outbox() -> None:
    published = asyncio.run(_redrive_outbox())
    print(f"Re-driven {published} pending outbox event(s).")


COMMANDS = {"seed-superadmin": seed_superadmin, "redrive-outbox": redrive_outbox}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python -m app.cli [{' | '.join(COMMANDS)}]", file=sys.stderr)
        raise SystemExit(2)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
