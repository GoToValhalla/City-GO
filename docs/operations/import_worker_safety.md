# Import-Worker Safety Framework (CITYGO-277)

## Why this exists

On 2026-07-10, a Kaliningrad full import ran on the former ~965 MiB
production host with no swap. The worker was OOM-killed and the backend became
unreachable behind nginx. The production VM has since been upgraded to about
2 GiB RAM, but the original safety principles remain mandatory.

## Contract

- Deploy never starts `import-worker`.
- The worker stays behind the `ops` Compose profile.
- The worker is manual-only through `CITY GO · OPS · Run Import Worker Safely`.
- Heavy work never runs inside the backend/web process.
- Safe mode remains enabled.
- Resource state must be verified before the worker loop starts.
- Unknown resource state fails closed.
- A blocked or failed job is never reported as a fake success.

## 2 GiB production resource policy

Current worker service limits:

```yaml
restart: "no"
mem_limit: 512m
memswap_limit: 512m
cpus: "0.75"
```

The service command runs a read-only resource preflight before the worker:

```text
python data/scripts/check_import_worker_resources.py
```

The preflight requires:

- host `MemAvailable >= 512 MiB`;
- effective cgroup memory limit is known;
- cgroup memory limit is at least `512 MiB`;
- all configured thresholds are valid positive integers.

Missing `/proc/meminfo`, unreadable cgroup files, an unlimited/unknown cgroup
limit, or insufficient memory aborts startup before queue processing.

## Safe-mode settings

| Setting | Production value | Meaning |
|---|---:|---|
| `IMPORT_WORKER_SAFE_MODE` | `true` | Keeps heavy-job safety checks enabled. |
| `IMPORT_WORKER_MAX_RUNTIME_SECONDS` | `300` | Bounded manual worker runtime. |
| `IMPORT_WORKER_BACKEND_HEALTH_URL` | `http://backend:8000/ready` | Backend readiness check before each worker iteration. |
| `IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB` | `512` | Required host memory before worker startup. |
| `IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB` | `512` | Required effective container/cgroup memory ceiling. |
| `IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY` | positive | Legacy heavy-job enable gate after resource preflight. `0` still blocks all heavy jobs. |

The legacy `MAX_FULL_IMPORT_PLACES_LOW_MEMORY` name must not be interpreted as
an exact live item-count guarantee. The current implementation uses `0` as a
static kill switch and a positive value as permission to continue to the
independent memory checks.

## Heavy and light jobs

Heavy sources:

- `admin_city_import`;
- `admin_city_enrichment`.

Light, bounded side jobs:

- `admin_address_enrichment`;
- `admin_photo_enrichment`;
- `admin_snapshot_refresh`.

When safe mode blocks a job, the job is marked terminal `failed` with a
truthful reason, a system-log event and an admin alert. It is not left
`running` or reported as successful.

## Manual workflow

Run GitHub Actions workflow `CITY GO · OPS · Run Import Worker Safely` with
confirmation:

```text
RUN_IMPORT_WORKER_SAFELY
```

The workflow checks public health/readiness, host memory and duplicate worker
state, starts only `import-worker`, monitors the bounded run, always stops the
worker, stores logs as an artifact and sends a Telegram summary.

The workflow does not deploy, pull images, execute SQL directly or start the
whole `ops` profile.

## Telegram bot runtime

The Telegram polling bot is a separate long-running service. It uses
`restart: unless-stopped`, because `restart: on-failure` leaves it permanently
stopped after a clean exit code 0. The bot has a 30-second graceful stop
period.

## Backend memory baseline

The first read-only sample after the VM upgrade showed approximately:

- backend: 515 MiB;
- PostgreSQL: 181 MiB;
- frontend: 8 MiB;
- host `MemAvailable`: 711 MiB.

One sample is insufficient to impose a new backend cgroup limit. The first
bounded import run must capture backend, worker and host memory over time.
See `runtime_resource_policy_2gb.md` for rollout and kill criteria.

## Recovering stale jobs

Use the existing admin recovery endpoint only after confirming no worker is
running:

```text
POST /admin/import-queue/mark-stalled
```

Recovery marks eligible old `running` jobs as terminal `stalled`. It does not
requeue or execute them. A new attempt remains a separate explicit action.

## Kill criteria

Stop immediately when any condition is true:

- `/api/health` or `/api/ready` stops returning 200;
- worker exits with code 137;
- host memory approaches the documented execution floor;
- backend latency degrades or 502 responses appear;
- worker/container resource values cannot be verified;
- queue or job state becomes contradictory.

## Prohibited actions

- Do not disable safe mode.
- Do not run heavy imports inside the web process.
- Do not start multiple workers.
- Do not use deploy as a worker launcher.
- Do not manually rewrite job rows to force execution.
- Do not raise limits without updating tests and this document in the same
  patch.
- Do not treat swap as a replacement for memory isolation.

## Rollout

1. Targeted tests and YAML validation.
2. Review exact Compose and preflight changes.
3. One full CI after approval.
4. One deploy.
5. Production smoke.
6. Read-only safety verification.
7. Confirm bot is running.
8. One bounded worker execution with memory evidence.
