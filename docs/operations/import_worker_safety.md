# Import-Worker Safety Framework (CITYGO-277)

## Why this exists

On 2026-07-10 (CITYGO-276), production deploy briefly auto-started
`import-worker`. It claimed a queued Kaliningrad full-import job (~3095 places)
on a ~965 MiB host with no swap. The worker was OOM-killed (`Exited (137)`),
and the backend became unreachable behind frontend/nginx (502 on
`/api/health`, `/api/ready`, and every admin endpoint) until `import-worker`
was stopped and backend was restarted.

## Contract

- **Deploy never starts `import-worker`.** `docker-compose.yml` keeps it
  behind the `ops` Compose profile; `deploy.yml` explicitly stops it and
  verifies it is not `running` after every deploy, failing the deploy if it is.
- **`import-worker` is manual-only**, via the guarded workflow described below.
  There is no automatic scheduler, no in-web fallback, and
  `admin_allow_in_web_worker_run_once` remains disabled — heavy import work
  must never run inside the backend/web process.
- **Full Kaliningrad-scale imports are blocked on the current host.**
  `IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY=0` means safe mode refuses
  *any* full-import/heavy job (`admin_city_import`, `admin_city_enrichment`)
  outright, regardless of the target city's actual place count — the host
  cannot safely run one at any size today.
- **Queued jobs stay queued.** A blocked job is not silently dropped: it is
  marked `failed` with a truthful `last_error` explaining why, and remains
  retryable through the existing admin retry action once the host is upgraded
  or the threshold is raised. No job is ever reported as a fake success.

## Resource isolation

`docker-compose.yml`, `import-worker` service:

```yaml
mem_limit: 384m
memswap_limit: 384m
cpus: "0.50"
restart: "no"
```

Plain `docker compose` service keys (not Swarm-only `deploy.resources`), since
this deployment does not use Swarm. `restart: "no"` is deliberate: a crashing
worker must never crash-loop and repeatedly compete for host memory/CPU.

## Worker safe-mode settings

Set on the `import-worker` service in `docker-compose.yml` (see
`core/config.py` for typed defaults, which are permissive for local/CI):

| Setting | Production value | Meaning |
|---|---|---|
| `IMPORT_WORKER_SAFE_MODE` | `true` | Enables all guards below. |
| `IMPORT_WORKER_MAX_RUNTIME_SECONDS` | `300` | Worker process stops itself after this many seconds. |
| `IMPORT_WORKER_BACKEND_HEALTH_URL` | `http://backend:8000/ready` | Checked before every claim iteration. |
| `IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB` | `256` | Used by the manual workflow's preflight check. |
| `IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY` | `0` | `0` = block all heavy jobs on this host. |

## Oversized/heavy job behavior

In `services/admin_city_import_tasks.py::run_queued_import_jobs`, before
processing a claimed job:

1. If safe mode is off (local/CI default) — no change, jobs run exactly as
   before this framework.
2. If safe mode is on and the job's source is heavy
   (`admin_city_import`/`admin_city_enrichment`) and the threshold is `0` —
   the job is marked `status="failed"`, `last_error` explains the safety
   guard and low-memory host, `finished_at` is set, and a `worker_job_blocked_safe_mode`
   system log entry plus an admin alert are recorded. The job is **not**
   processed, **not** left running, **not** reported as success.
3. Light side-tasks (`admin_address_enrichment`, `admin_photo_enrichment`,
   `admin_snapshot_refresh`) are never blocked by this guard — they are
   already bounded, per-place operations, not full-city scans.

## Backend health guard

`data/scripts/run_admin_import_worker.py::run_worker_loop` checks
`backend_is_healthy(health_url)` before every iteration. On failure, the loop
breaks immediately (no job is claimed), an admin alert is sent, and the
process exits — it does not keep retrying against a dead backend. A
`max_runtime_seconds` bound stops the loop even if backend stays healthy.

## How to run the safe workflow

GitHub Actions → `CITY GO · OPS · Run Import Worker Safely`
(`.github/workflows/run-import-worker-safe.yml`), `workflow_dispatch` only.

1. Set `confirmation` to exactly `RUN_IMPORT_WORKER_SAFELY`.
2. Optionally set `max_runtime_seconds` (default `300`).
3. The workflow: preflights (public `/api/health` and `/api/ready` must both
   be `200`; available host memory must be ≥256 MB; `import-worker` must not
   already be running) → starts only `import-worker`
   (`docker compose up -d --no-deps import-worker`, never the whole `ops`
   profile) → monitors every 10 seconds, stopping on worker exit, backend
   health failure, or timeout → **always** stops `import-worker` in cleanup,
   even on failure → collects `docker compose ps -a`, worker/backend/frontend
   logs, `docker stats --no-stream`, `free -h` → uploads
   `safe-import-worker-run-report` as an artifact → sends a Telegram summary.

The workflow never deploys, pulls images, mutates the DB directly, or starts
any other `ops` service.

## Recovering a stale running job

If `import-worker` does not exist (confirmed via `docker compose ps -a` or the
read-only verification workflow) but the queue still shows a job stuck in
`status="running"` — e.g. from before this framework existed, or from a worker
that was stopped/killed mid-job — use the existing manual recovery endpoint:

```
POST /admin/import-queue/mark-stalled
```

(`routers/admin_import_queue.py::mark_stuck_import_jobs`). This is the same
endpoint the admin UI's "Пометить зависшие" button calls.

**What it does:**

- Only affects jobs with `status == "running"` that have exceeded
  `MAX_RUNNING_SECONDS` (1 hour) since `started_at`/`updated_at`/`created_at`.
- Transitions each matched job to `status="stalled"` (an existing terminal
  status — no new enum, no migration), sets `current_step="error"`,
  `finished_at=now`, and `last_error="Recovered stale import job: no active
  worker heartbeat / worker process absent"` (only if the job doesn't already
  have a more specific error).
- Records a `manual_stalled_recovery` system log entry and sends an admin
  alert (`"Import queue recovered stuck jobs"`).
- **Does not requeue or re-run the job.** Recovery only marks the current
  stuck attempt as terminal; if a fresh attempt is wanted, that is a separate,
  explicit retry action the operator takes afterward — never automatic.
- Is idempotent: a job already recovered (now `stalled`, not `running`) is not
  touched by a second call; a job that finished normally (`success`,
  `failed`, etc.) was never a candidate and is never touched.
- Determines staleness purely from the job's own timestamps — it does not
  inspect Docker/container state itself. The operator is responsible for
  separately confirming (e.g. via the read-only verification workflow) that no
  worker is actually still processing the job before recovering it.

**After recovery:** re-check `GET /admin/import-queue` to confirm `running`
and `stalled_running` both return to `0` for that job, then re-run the
read-only verification workflow before considering any manual worker
execution — see "What NOT to do" below.

## Kill criteria (stop immediately if any of these are true)

- Public backend health is not `200` on `/api/health` or `/api/ready`.
- Available host memory drops below the configured minimum (256 MB).
- `import-worker` container exits with code `137` (OOM-killed) or any
  non-`running` state.
- API latency degrades noticeably or any `/api/*` route returns 502.

The safe workflow already enforces these automatically; if running anything
manually outside that workflow, apply the same criteria by hand.

## What NOT to do

- Do not trigger a full import or "retry collection" from the admin UI while
  this framework is the only mitigation in place — queued jobs will simply be
  marked `failed` by the safety guard (truthfully, not silently), and no
  heavy job will actually run on this host.
- Do not manually update job rows/status in the database to force a job
  through.
- Do not re-enable `admin_allow_in_web_worker_run_once` to work around a
  stopped worker — this reintroduces the original in-process contention risk
  it was built to prevent.
- Do not deploy just to start `import-worker` — deploy must keep it stopped;
  use the guarded manual workflow instead.
- Do not raise `IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY` above `0` or
  disable `IMPORT_WORKER_SAFE_MODE` on the current host without first
  confirming a real memory/CPU upgrade — this document's thresholds are a
  starting point, not a target to routinely override.
- Do not run the safe manual worker workflow while the queue state is not
  truthful (e.g. a stuck `running` job with no corresponding worker) — recover
  it first via `POST /admin/import-queue/mark-stalled`, re-confirm
  `GET /admin/import-queue` shows `running`/`stalled_running` at `0`, and only
  then re-run the read-only verification workflow to confirm the effective
  compose config still matches expectations before considering any worker run.

## Out of scope for this framework

Running the safe workflow, deploying, performing the actual Kaliningrad full
import, real resource profiling under load, a host upgrade, a streaming
parser rewrite, or a Celery/queue architecture migration are all explicitly
out of scope here — they are separate, later decisions.
