# CITY GO runtime resource policy for the 2 GiB VM

Date: 2026-07-11  
Status: proposed rollout contract  
Related: CITYGO-223, CITYGO-264

## Production evidence

Read-only diagnostics after the VM upgrade and reboot showed:

- physical memory visible to Linux: about 1.8 GiB;
- steady-state `MemAvailable`: about 711 MiB;
- backend container usage: about 515 MiB;
- PostgreSQL container usage: about 181 MiB;
- frontend container usage: about 8 MiB;
- no swap;
- import-worker stopped;
- Telegram bot exited cleanly and stayed stopped under `restart: on-failure`.

These values are a baseline, not a permanent capacity guarantee.

## Import-worker policy

The import-worker remains:

- manual-only;
- behind the `ops` Compose profile;
- disabled during normal deploy;
- limited to one queued job per iteration;
- bounded to 300 seconds per manual run;
- configured with `restart: "no"`.

The proposed 2 GiB-host limits are:

```yaml
mem_limit: 512m
memswap_limit: 512m
cpus: "0.75"
```

Before the worker loop starts, `check_import_worker_resources.py` must verify:

1. host `MemAvailable >= 512 MiB`;
2. effective cgroup memory limit is known and at least `512 MiB`;
3. invalid, missing, unlimited, or unreadable values fail closed.

Safe mode remains enabled. The old production value
`IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY=0` was a static kill switch
for the former 1 GiB host. A positive production value only permits the heavy
job path after the independent host/cgroup preflight; it must not be treated
as a trustworthy live item-count limit.

## Backend memory finding

The backend was the largest steady-state consumer at about 515 MiB. This
patch does not impose a new backend cgroup cap because one read-only sample is
not enough to choose a safe ceiling. During the first bounded import run,
collect at least:

- backend memory usage before worker start;
- backend memory usage every 10 seconds;
- worker memory usage every 10 seconds;
- host `MemAvailable` every 10 seconds;
- backend health and readiness.

A backend cap may be proposed only after the observed peak and normal traffic
variance are known.

## Telegram bot policy

The bot is a long-running polling service. `restart: on-failure` does not
restart it after a clean exit code 0, which is exactly the observed production
state. The service therefore uses `restart: unless-stopped` and a 30-second
graceful stop period. This does not start the bot when an operator explicitly
stops it.

## Rollout order

1. Run targeted tests and YAML validation on the branch.
2. Review the exact Compose diff and worker preflight output contract.
3. Merge only after approval.
4. Run one full CI.
5. Deploy once.
6. Run production smoke.
7. Verify bot is `running`.
8. Run the read-only worker safety diagnostic.
9. Requeue one explicit import attempt if required.
10. Run the guarded worker workflow for at most 300 seconds.

## Kill criteria

Stop the worker immediately when any condition is true:

- `/api/health` or `/api/ready` is not 200;
- host `MemAvailable < 192 MiB` during execution;
- worker exits with code 137;
- backend memory grows continuously without stabilizing;
- backend latency or 502 responses appear;
- the resource preflight cannot read the cgroup limit;
- the job state becomes contradictory or loses heartbeat.

Do not disable safe mode, run the worker in the web process, add swap as a
substitute for memory isolation, or start multiple import workers.
