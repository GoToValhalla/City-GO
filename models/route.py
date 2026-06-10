from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель маршрута.
# Нужна для хранения готовых сценариев прогулок и последовательностей мест.
class Route(Base):
    __tablename__ = "routes"

    # Уникальный идентификатор маршрута.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор города, к которому относится маршрут.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)

    # Уникальный slug маршрута для URL.
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Название маршрута.
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Короткое описание маршрута.
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Примерная длительность маршрута в минутах.
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Примерная дистанция маршрута в километрах.
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Режим маршрута: walk / public_transport / mixed.
    route_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="walk")

    # Признак активности маршрута.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь маршрута с городом.
    city = relationship("City", back_populates="routes")

    # Связь маршрута с точками через route_places.
    route_places = relationship("RoutePlace", back_populates="route")