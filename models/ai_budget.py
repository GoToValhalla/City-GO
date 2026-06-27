"""AI budget ledgers and reservations."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AIBudgetLedger(Base):
    __tablename__ = "ai_budget_ledgers"
    __table_args__ = (UniqueConstraint("scope", "period_key", name="uq_ai_budget_ledgers_scope_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reserved_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spent_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIBudgetReservation(Base):
    __tablename__ = "ai_budget_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="admin", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="reserved", index=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    day_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    month_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    failure_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="spend_reserved_on_unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
