# HANDOFF — когда вернёшься к ноуту

## Автономно сделано (без push)

- `.cursor/permissions.json` — allowlist всего кроме `git push` и prod deploy
- `docs/routes/almaty_second_run_report.md` — отчёт по доступным данным
- `data/audit/almaty_second_run/before.json`, `after_partial.json`
- Workflow collect: max 3 poll, partial file fetch без DONE

## Нужен один клик (prod/GitHub)

```bash
git push origin master
gh workflow run prod-almaty-second-run.yml -f mode=collect -f apply_slug=false -f address_limit=50 -f image_limit=50
```

Если collect пустой — затем `mode=full` с лимитами 30/30.

## Не дергать

- Автопубликацию города
- `apply_slug=true` (slug уже `almaty`)
