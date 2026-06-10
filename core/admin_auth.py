"""
Серверная аутентификация для admin/write endpoints.

Схема: Bearer-token из заголовка Authorization.
Токен сравнивается через hmac.compare_digest (защита от timing attack).

Использование:
    @router.post("/admin/foo")
    def create_foo(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
        ...  # auth.actor_id содержит идентификатор действующего админа
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from core.config import settings


@dataclass(frozen=True)
class AdminContext:
    """Контекст авторизованного администратора."""

    actor_id: str
    actor_role: str
    auth_source: str


def _extract_bearer(authorization: str | None) -> str | None:
    """Извлекает токен из заголовка 'Authorization: Bearer <token>'."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[len("Bearer "):]
    return None


def admin_required(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminContext:
    """
    FastAPI dependency: проверяет admin Bearer-token.

    Raises:
        401 — заголовок отсутствует или не является Bearer-токеном.
        403 — токен неверный.
        503 — ADMIN_API_TOKEN не настроен в окружении.
    """
    token = _extract_bearer(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Authorization header required")

    expected = settings.admin_api_token
    if not expected:
        raise HTTPException(status_code=503, detail="Admin authentication not configured")

    if not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    return AdminContext(
        actor_id="admin-api",
        actor_role="admin",
        auth_source="admin_token",
    )
