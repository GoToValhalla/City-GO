from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель категории места.
# Нужна для хранения справочника категорий: cafe, walk, museum и т.д.
class Category(Base):
    __tablename__ = "categories"

    # Уникальный идентификатор категории.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Уникальный код категории для внутреннего использования.
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название категории на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Признак активности категории.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь категории с местами.
    places = relationship("Place", back_populates="category_ref")
