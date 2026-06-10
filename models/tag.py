from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель тега.
# Нужна для сценарной и тематической фильтрации мест.
class Tag(Base):
    __tablename__ = "tags"

    # Уникальный идентификатор тега.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Уникальный код тега для внутреннего использования.
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название тега на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Признак активности тега.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь тега со связями place_tags.
    place_tags = relationship("PlaceTag", back_populates="tag")
