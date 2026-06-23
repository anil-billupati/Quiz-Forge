"""Cursor pagination envelope (api-contracts.md §Pagination).

List endpoints return ``Page[T]`` with the items plus an opaque ``next_cursor``
and ``has_more`` flag.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
