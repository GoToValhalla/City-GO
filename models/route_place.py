from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи маршрутов и мест.
# Нужна для хранения списка точек внутри маршрута.
class RoutePlace(Base):
    __tablename__ = "route_places"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор маршрута.
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Порядок точки внутри маршрута.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с маршрутом.
    route = relationship("Route", back_populates="route_places")

    # Связь с местом.
    place = relationship("Place", back_populates="route_places")