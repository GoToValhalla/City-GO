from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи мест и тегов.
# Нужна для many-to-many связи между places и tags.
class PlaceTag(Base):
    __tablename__ = "place_tags"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Идентификатор тега.
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False, index=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с местом.
    place = relationship("Place", back_populates="place_tags")

    # Связь с тегом.
    tag = relationship("Tag", back_populates="place_tags")
