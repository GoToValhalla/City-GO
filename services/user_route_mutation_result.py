from __future__ import annotations

from dataclasses import dataclass

from schemas.user_route import UserRouteState


@dataclass(frozen=True)
class RouteMutationResult:
    """Explicit domain outcome for one route-state mutation attempt.

    Rejected operations never carry a replacement state and therefore cannot be
    mistaken for a successful revision transition by the lifecycle owner.
    """

    accepted: bool
    state: UserRouteState | None = None
    reason: str | None = None

    @classmethod
    def success(cls, state: UserRouteState) -> "RouteMutationResult":
        return cls(accepted=True, state=state)

    @classmethod
    def rejected(cls, reason: str) -> "RouteMutationResult":
        text = str(reason or "Route mutation was rejected.").strip()
        return cls(accepted=False, reason=text)


__all__ = ["RouteMutationResult"]
