# MVP Release Candidate

## Scope

MVP RC focuses on one city first: Зеленоградск.

Included:
- Backend route source of truth.
- Telegram route/search/correction flows.
- Place import, coverage, verification queue.
- Route/import/request/Telegram observability.
- Basic UI route and place workflows.

Not included:
- ML ranking.
- Multi-country rollout.
- Social/gamification.
- Full transit routing.

## Release Order

1. Prepare data pack and run dry-run import.
2. Run backup.
3. Apply migrations.
4. Run real import.
5. Enqueue stale places and review queue.
6. Start backend and Telegram bot.
7. Run release smoke.
8. Run UI Playwright smoke.
9. Monitor route analytics and Telegram events.

## MVP Metrics

- `route_quality_score` average.
- warning rate.
- p95 route build latency.
- import success rate.
- place coverage score.
- Telegram actions per session.
- routes built per day.
