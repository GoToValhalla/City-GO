from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи подборок и мест.
# Нужна для хранения списка мест внутри подборки.
class CollectionPlace(Base):
    __tablename__ = "collection_places"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор подборки.
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Порядок места внутри подборки.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с подборкой.
    collection = relationship("Collection", back_populates="collection_places")

    # Связь с местом.
    place = relationship("Place", back_populates="collection_places")
