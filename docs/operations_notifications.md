# Operations Notifications

City GO uses one Telegram operations chat configured by:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Notification sources

### Full Autotests

`.github/workflows/ci.yml` sends its own grouped total report.

### Production Deploy

`.github/workflows/deploy.yml` always sends the final build/deploy result through `scripts/send_telegram_notification.py`.

Notification failure is visible as a failed `Notify deploy result` job. It is no longer hidden by `continue-on-error`.

During deployment, Telegram credentials from GitHub Secrets replace values in `/srv/app/.env` on every run. This prevents backend and workers from retaining an obsolete bot token after secret rotation.

### Operational GitHub workflows

`.github/workflows/operations-notifications.yml` listens for completion of:

- API Error Monitor;
- Admin Smoke;
- Backend Error Diagnostics;
- City Import;
- Data Enrichment;
- Prod DB Repair;
- Production Docker Cleanup;
- Production Health;
- Recover Frontend.

Failures always notify. Frequent successful health/smoke schedules remain silent. Successful mutating operations such as import, enrichment, repair, cleanup and recovery notify.

### Runtime backend workers

`services/admin_alert_service.py` sends import/enrichment job results and incidents from production containers.

`data/scripts/run_admin_import_worker.py` also handles failures outside an individual job, including database connection and runner startup failures. Alerts are rate-limited:

- first consecutive failure;
- third consecutive failure;
- every tenth consecutive failure;
- one recovery message after the worker succeeds again.

## Deployment gates

Production deploy fails before changing containers when Telegram secrets are absent. After containers restart, the deploy checks that both `backend` and `import-worker` loaded a token and chat ID.

## Delivery helper

`scripts/send_telegram_notification.py`:

- sends form-urlencoded UTF-8 text;
- validates Telegram JSON `ok=true`;
- retries network and API failures three times;
- limits messages to Telegram's safe text size;
- exits non-zero when delivery fails.

## Troubleshooting

1. Open the failed workflow and locate the notification job.
2. Search logs for `telegram_notification_failed` or `admin_alert_send_failed`.
3. Verify GitHub Secrets contain the current bot token and numeric/chat identifier.
4. Run Production Deploy to rotate the runtime `.env` values and recreate backend/import-worker.
5. For runtime incidents, inspect `docker compose logs import-worker backend`.
