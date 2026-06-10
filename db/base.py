"""
Базовый Declarative-класс SQLAlchemy 2.x для всех ORM-моделей приложения.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Корень дерева моделей; таблицы наследуются от этого класса."""

    pass
