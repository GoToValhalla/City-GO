"""Atomic-ish AI budget reservation helpers.

PostgreSQL uses SELECT FOR UPDATE on period ledger rows. SQLite ignores row
locks, but the same code path is still useful for service tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from models.ai_budget import AIBudgetLedger, AIBudgetReservation


@dataclass(frozen=True)
class BudgetEstimate:
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


def estimate_cost(
    *,
    text: str,
    input_usd_per_1m: float,
    output_usd_per_1m: float,
    output_tokens: int,
) -> BudgetEstimate:
    input_tokens = max(1, len(text) // 4)
    output_tokens = max(1, output_tokens)
    cost = (input_tokens / 1_000_000 * input_usd_per_1m) + (output_tokens / 1_000_000 * output_usd_per_1m)
    return BudgetEstimate(input_tokens=input_tokens, output_tokens=output_tokens, estimated_cost_usd=round(cost, 8))


def reserve_budget(
    db: Session,
    *,
    actor: str,
    estimated_cost_usd: float,
) -> AIBudgetReservation:
    if estimated_cost_usd > settings.ai_max_job_cost_usd:
        raise ValueError("job_cost_limit")

    now = datetime.utcnow()
    day_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    _lock_budget(db, day_key=day_key, month_key=month_key)
    reap_expired_reservations(db, now=now)
    daily = _ledger(db, scope="daily", period_key=day_key)
    monthly = _ledger(db, scope="monthly", period_key=month_key)

    if daily.spent_usd + daily.reserved_usd + estimated_cost_usd > settings.ai_daily_budget_usd:
        raise ValueError("daily_budget_limit")
    if monthly.spent_usd + monthly.reserved_usd + estimated_cost_usd > settings.ai_monthly_stop_usd:
        raise ValueError("monthly_budget_stop")

    daily.reserved_usd = round(daily.reserved_usd + estimated_cost_usd, 8)
    monthly.reserved_usd = round(monthly.reserved_usd + estimated_cost_usd, 8)
    reservation = AIBudgetReservation(
        actor=actor,
        status="reserved",
        estimated_cost_usd=estimated_cost_usd,
        day_key=day_key,
        month_key=month_key,
        expires_at=now + timedelta(seconds=settings.ai_budget_reservation_ttl_seconds),
    )
    db.add_all([daily, monthly, reservation])
    db.flush()
    return reservation


def attach_reservation(db: Session, *, reservation: AIBudgetReservation, task_run_id: int) -> None:
    reservation.task_run_id = task_run_id
    db.add(reservation)
    db.flush()


def commit_budget(
    db: Session,
    *,
    reservation: AIBudgetReservation,
    actual_cost_usd: float | None,
    status: str = "committed",
) -> float:
    cost = reservation.estimated_cost_usd if actual_cost_usd is None else max(0.0, actual_cost_usd)
    if not _transition_reserved_reservation(db, reservation=reservation, new_status=status):
        return 0.0
    daily = _ledger(db, scope="daily", period_key=reservation.day_key)
    monthly = _ledger(db, scope="monthly", period_key=reservation.month_key)
    for ledger in (daily, monthly):
        ledger.reserved_usd = round(max(0.0, ledger.reserved_usd - reservation.estimated_cost_usd), 8)
        ledger.spent_usd = round(ledger.spent_usd + cost, 8)
        db.add(ledger)
    reservation.actual_cost_usd = cost
    db.add(reservation)
    db.flush()
    return cost


def release_budget(db: Session, *, reservation: AIBudgetReservation) -> None:
    if not _transition_reserved_reservation(db, reservation=reservation, new_status="released"):
        return
    daily = _ledger(db, scope="daily", period_key=reservation.day_key)
    monthly = _ledger(db, scope="monthly", period_key=reservation.month_key)
    for ledger in (daily, monthly):
        ledger.reserved_usd = round(max(0.0, ledger.reserved_usd - reservation.estimated_cost_usd), 8)
        db.add(ledger)
    reservation.actual_cost_usd = 0.0
    db.add(reservation)
    db.flush()


def reap_expired_reservations(db: Session, *, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    reservations = (
        db.query(AIBudgetReservation)
        .filter(AIBudgetReservation.status == "reserved", AIBudgetReservation.expires_at < now)
        .with_for_update()
        .all()
    )
    expired_count = 0
    for reservation in reservations:
        if not _transition_reserved_reservation(db, reservation=reservation, new_status="expired"):
            continue
        daily = _ledger(db, scope="daily", period_key=reservation.day_key)
        monthly = _ledger(db, scope="monthly", period_key=reservation.month_key)
        for ledger in (daily, monthly):
            ledger.reserved_usd = round(max(0.0, ledger.reserved_usd - reservation.estimated_cost_usd), 8)
            db.add(ledger)
        reservation.actual_cost_usd = 0.0
        db.add(reservation)
        expired_count += 1
    db.flush()
    return expired_count


def _transition_reserved_reservation(
    db: Session,
    *,
    reservation: AIBudgetReservation,
    new_status: str,
) -> bool:
    current = (
        db.query(AIBudgetReservation)
        .filter(AIBudgetReservation.id == reservation.id)
        .with_for_update()
        .first()
    )
    if current is None or current.status != "reserved":
        if current is not None:
            db.refresh(reservation)
        return False
    current.status = new_status
    reservation.status = new_status
    db.add(current)
    db.flush()
    return True


def _ledger(db: Session, *, scope: str, period_key: str) -> AIBudgetLedger:
    ledger = (
        db.query(AIBudgetLedger)
        .filter(AIBudgetLedger.scope == scope, AIBudgetLedger.period_key == period_key)
        .with_for_update()
        .first()
    )
    if ledger is not None:
        return ledger
    ledger = AIBudgetLedger(scope=scope, period_key=period_key, reserved_usd=0.0, spent_usd=0.0)
    db.add(ledger)
    db.flush()
    return ledger


def _lock_budget(db: Session, *, day_key: str, month_key: str) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    lock_key = f"citygo_ai_budget:{day_key}:{month_key}"
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": lock_key})
