# Backup / Restore

MVP backup process uses PostgreSQL custom-format dumps.

## Backup

```bash
export DATABASE_URL="postgresql://..."
BACKUP_DIR=backups scripts/backup_db.sh
```

The script prints the created dump path.

## Restore

Restore is intentionally explicit because it can replace data in the target DB.

```bash
export DATABASE_URL="postgresql://..."
scripts/restore_db.sh backups/citygo_YYYYMMDDTHHMMSSZ.dump
```

## Restore Check

1. Restore into a temporary database.
2. Run `alembic upgrade head`.
3. Start backend.
4. Run `BASE_URL=http://127.0.0.1:8000 scripts/release_smoke.sh`.

Do not mark backups as production-ready until restore has been tested.
