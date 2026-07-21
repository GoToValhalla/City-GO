from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitRule:
    path_prefix: str
    methods: frozenset[str]
    limit: int
    window_seconds: float = 60.0
    policy_key: str | None = None

    @property
    def key(self) -> str:
        return self.policy_key or self.path_prefix


WRITE = frozenset({"POST", "PUT", "PATCH", "DELETE"})
RULES: tuple[RateLimitRule, ...] = (
    RateLimitRule("/v1/user-routes/build", frozenset({"POST"}), 20),
    RateLimitRule("/v1/user-routes/preview", frozenset({"POST"}), 20),
    RateLimitRule("/v1/user-routes", WRITE, 30),
    RateLimitRule("/v1/recommendations/route", frozenset({"POST"}), 20, policy_key="recommendations-route"),
    RateLimitRule("/recommendations/route", frozenset({"POST"}), 20, policy_key="recommendations-route"),
    RateLimitRule("/routes/generate", frozenset({"POST"}), 20),
    RateLimitRule("/routes/replan", frozenset({"POST"}), 20),
    RateLimitRule("/routes/random", frozenset({"POST"}), 30),
    RateLimitRule("/routes/walking-geometry", frozenset({"POST"}), 30),
    RateLimitRule("/routes", WRITE, 30),
    RateLimitRule("/route-sessions", frozenset({"POST", "PATCH"}), 30),
    RateLimitRule("/ai", frozenset({"POST", "GET"}), 20),
    RateLimitRule("/debug-reports", frozenset({"POST"}), 10),
    RateLimitRule("/place-discovery", frozenset({"POST"}), 20),
    RateLimitRule("/route-feedback", frozenset({"POST"}), 30),
    RateLimitRule("/user-signals", frozenset({"POST"}), 60),
    RateLimitRule("/place-seed", frozenset({"POST"}), 10),
    RateLimitRule("/v1/verification", frozenset({"POST"}), 20),
    RateLimitRule("/geo", frozenset({"POST"}), 30),
    RateLimitRule("/navigation-events", frozenset({"POST"}), 60),
    RateLimitRule("/place-taxonomy/diagnostics", frozenset({"POST"}), 30),
    RateLimitRule("/telegram-bot/webhook", frozenset({"POST"}), 120),
    RateLimitRule("/me", WRITE, 30),
    RateLimitRule("/identity", frozenset({"POST"}), 20),
    RateLimitRule("/places", WRITE, 30),
    RateLimitRule("/reviews", WRITE, 30),
    RateLimitRule("/admin/moderation", frozenset({"POST"}), 20),
)
