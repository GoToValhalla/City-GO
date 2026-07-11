# Import-Worker Safety Framework (CITYGO-277 / CITYGO-280)

## Why this exists

On 2026-07-10, production deploy briefly auto-started `import-worker` on the
former ~965 MiB/no-swap host. A heavy import ended with worker exit code `137`,
public backend/API 502 responses, and recovery only after the worker stopped and
the backend restarted.

The production VM now exposes approximately 1.8 GiB RAM, with an observed idle
`MemAvailable` around 711 MiB. The upgrade removes the stale unconditional
heavy-job block, but it does not remove the need for hard isolation and
fail-closed resource checks.

## Immutable operating contract

- Deploy never starts `import-worker`.
- `import-worker` remains behind the `ops` profile.
- Execution is manual-only through `CITY GO · OPS · Run Import Worker Safely`.
- One queued job is processed per controlled run (`IMPORT_WORKER_BATCH_LIMIT=1`).
- Heavy work never runs inside the backend/web process.
- Safe mode remains enabled.
- Unknown host or cgroup memory state fails closed.
- `restart: "no"` remains mandatory.
- No all-city APPLY is permitted while the new envelope is under validation.
- A failed or blocked worker run must never be reported as success.

## Production resource envelope

Observed idle baseline after the VM upgrade:

| Resource | Observed value |
|---|---:|
| Host RAM visible to Linux | ~1.8 GiB |
| Host `MemAvailable` | ~711 MiB |
| Backend container | ~515 MiB |
| PostgreSQL container | ~181 MiB |
| Frontend container | ~8 MiB |
| Swap | 0 |

These values are a measurement baseline, not guaranteed free capacity.

## Worker Compose contract

```yaml
profiles: ["ops"]
restart: "no"
mem_limit: 512m
memswap_limit: 512m
cpus: "0.50"
stop_grace_period: 30s
```

The worker command runs a read-only resource preflight before queue processing:

```text
python data/scripts/check_import_worker_resources.py
```

## Startup resource guard

Production values:

| Setting | Value | Meaning |
|---|---:|---|
| `IMPORT_WORKER_SAFE_MODE` | `true` | Keeps heavy-job and runtime guards enabled. |
| `IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB` | `650` | Heavy-run host startup floor. |
| `IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB` | `512` | Minimum finite cgroup limit. |
| `IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB` | `400` | Minimum cgroup headroom before worker start. |
| `IMPORT_WORKER_MAX_RUNTIME_SECONDS` | `300` | Maximum controlled run duration. |
| `IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB` | `256` | Runtime emergency host-memory floor. |
| `IMPORT_WORKER_RUNTIME_CGROUP_PERCENT` | `85` | Runtime cgroup soft-stop threshold. |
| `IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY` | `1` | Explicit heavy-job enable switch after resource preflight. |

`IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY` is legacy-named. In the
current implementation it is an enable/disable gate, not a trustworthy live
place-count cap. `0` blocks all heavy jobs; a positive value only permits the
job to continue to the independent resource guards.

The preflight reads:

- host `MemAvailable` from `/proc/meminfo`;
- cgroup v2 `memory.max` and `memory.current`, or;
- cgroup v1 `memory.limit_in_bytes` and `memory.usage_in_bytes`.

Startup is refused when:

- host memory cannot be read;
- host `MemAvailable < 650 MiB`;
- cgroup limit or usage cannot be read;
- cgroup limit is `max`, unbounded, invalid, or below 512 MiB;
- cgroup headroom is below 400 MiB;
- the heavy-job enable switch remains `0`;
- public `/api/health` or `/api/ready` is not 200;
- another worker instance is already running.

## Heavy and light jobs

Heavy sources remain:

- `admin_city_import`;
- `admin_city_enrichment`.

The static safe-mode gate applies only to these sources. Bounded side tasks
(address, photo and snapshot work) keep their existing behavior. The guarded
production workflow is currently intended for the controlled heavy Job #9 run;
it applies the conservative 650 MiB host startup floor before starting the
container.

## Runtime guard

The manual workflow samples every 5 seconds and records:

- worker container state;
- public `/api/health` and `/api/ready` status;
- host `MemAvailable`;
- worker cgroup usage percentage and human-readable usage;
- final exit code and Docker `OOMKilled` state.

The workflow stops the worker with a 30-second SIGTERM grace period when:

- public health or readiness is non-200;
- host `MemAvailable < 256 MiB`;
- worker cgroup usage reaches 85%;
- the 300-second runtime expires;
- the worker exits on its own.

`run_admin_import_worker.py` converts SIGTERM/SIGINT into an exception while an
active job is running. The existing per-job failure handler then records a
truthful terminal failure instead of leaving the job silently running. If the
process is hard-killed before Python can handle the signal, Docker exit code,
`OOMKilled`, queue state and the existing stalled-job recovery path remain the
operator evidence.

## Manual execution procedure

1. Confirm exact deployed SHA and green CI for that SHA.
2. Confirm production deploy and smoke are green.
3. Confirm queue truth: one intended queued job, no running/stalled worker job.
4. Confirm `import-worker` is not running.
5. Confirm idle `MemAvailable >= 650 MiB`.
6. Run GitHub Actions workflow `CITY GO · OPS · Run Import Worker Safely`.
7. Enter confirmation exactly `RUN_IMPORT_WORKER_SAFELY`.
8. Keep runtime at 300 seconds for the first Job #9 measurement run.
9. Monitor the workflow artifact and Telegram summary.
10. After the run, verify worker exit state, queue state, job terminal state,
    backend/DB health and data-regression indicators.

The workflow starts only `import-worker` with
`docker compose up -d --no-deps import-worker`. It does not deploy, pull images,
run SQL, start the whole `ops` profile, restart backend/DB, or enqueue work.

## Production kill criteria

Stop and do not retry automatically if any occurs:

- `/api/health` or `/api/ready` becomes non-200;
- any public API begins returning 502;
- host `MemAvailable` falls below 256 MiB;
- worker reaches 85% of its 512 MiB cgroup limit;
- worker exits 137 or Docker reports `OOMKilled=true`;
- backend or PostgreSQL restarts;
- queue state and DB job state diverge;
- job remains `running` after the worker is gone;
- runtime expires without a truthful terminal or retryable state;
- source errors are followed by destructive reconciliation;
- address, photo, publication or visibility counts regress unexpectedly.

## Recovering a stale running job

Only after independently confirming that no worker process exists, use the
existing supported recovery action:

```text
POST /admin/import-queue/mark-stalled
```

This marks eligible stale running jobs terminal and records operational logs.
It does not requeue or rerun the job. Do not mutate job rows directly.

## Restrictions

- Do not disable safe mode.
- Do not raise the worker cap or lower floors based on a single successful run.
- Do not add swap without explicit approval.
- Do not use in-web worker execution.
- Do not start the worker from deploy.
- Do not run all-city APPLY.
- Do not treat the first Job #9 run as proof that every city/payload fits the
  same envelope.

## Remaining known risk

Full HTTP response, parsed JSON and normalized lists can still be materialized
before chunked ORM processing. Chunk commits reduce transaction/session growth
but do not eliminate that peak. If Job #9 approaches the 512 MiB cap, the next
engineering step is collection/normalization streaming or bounded source
partitioning—not a blind memory-limit increase.
