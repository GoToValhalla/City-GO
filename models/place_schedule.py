from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель расписания места.
# Нужна для проверки, открыто ли место в конкретный день и время.
class PlaceSchedule(Base):
    __tablename__ = "place_schedules"

    # Уникальный идентификатор записи расписания.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # День недели в формате: mon, tue, wed, thu, fri, sat, sun.
    weekday: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Время открытия.
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Время закрытия.
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Признак, что в этот день место закрыто.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь расписания с местом.
    place = relationship("Place", back_populates="schedules")
