"""Helpers reutilizables para slugs públicos de negocios."""
import re
import unicodedata
from typing import Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant


def generate_slug(name: str) -> str:
    """Genera un slug URL-safe a partir de un nombre comercial."""
    normalized = unicodedata.normalize("NFD", name or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "negocio"


def ensure_unique_slug(
    db: Session,
    base_slug: str,
    *,
    exclude_tenant_id: Optional[int] = None,
) -> str:
    """Garantiza unicidad de slug agregando sufijos -2, -3, etc."""
    base = generate_slug(base_slug)
    candidate = base
    suffix = 2

    while True:
        query = db.query(Tenant).filter(Tenant.slug == candidate)
        if exclude_tenant_id is not None:
            query = query.filter(Tenant.id != exclude_tenant_id)
        if not query.first():
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1

