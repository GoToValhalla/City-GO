"""
Чтение тегов мест (таблица tags) для фильтрации и админки.
"""

from sqlalchemy.orm import Session

from models.tag import Tag


# Возвращает список всех тегов из базы данных.
def get_tags(db: Session) -> list[Tag]:
    return db.query(Tag).all()


# Возвращает один тег по его идентификатору.
def get_tag_by_id(db: Session, tag_id: int) -> Tag | None:
    return db.query(Tag).filter(Tag.id == tag_id).first()


# Возвращает один тег по его коду.
def get_tag_by_code(db: Session, code: str) -> Tag | None:
    return db.query(Tag).filter(Tag.code == code).first()
