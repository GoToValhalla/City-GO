from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель подборки.
# Нужна для ручных сценариев и тематических наборов мест.
class Collection(Base):
    __tablename__ = "collections"

    # Уникальный идентификатор подборки.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор города, к которому относится подборка.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)

    # Уникальный slug подборки для URL.
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Название подборки.
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Короткое описание подборки.
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Признак активности подборки.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь подборки с городом.
    city = relationship("City", back_populates="collections")

    # Связь подборки с местами через collection_places.
    collection_places = relationship("CollectionPlace", back_populates="collection")
