"""Small helpers for server-side pagination responses."""
from __future__ import annotations

import math
from typing import Iterable

def clamp_page(page: int) -> int:
    return max(page, 1)


def clamp_page_size(page_size: int) -> int:
    return min(max(page_size, 1), 100)


def paginate_query(query, page: int, page_size: int) -> dict:
    page = clamp_page(page)
    page_size = clamp_page_size(page_size)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def serialize_page(page_data: dict, items: Iterable[dict]) -> dict:
    return {**page_data, "items": list(items)}
