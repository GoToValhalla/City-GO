from sqlalchemy import Column, Integer, MetaData, Table, create_engine
from sqlalchemy.orm import sessionmaker

from services.place_count_service import get_query_total


def test_get_query_total_returns_total_before_pagination() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    test_items = Table(
        "test_items",
        metadata,
        Column("id", Integer, primary_key=True),
    )

    metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    db.execute(
        test_items.insert(),
        [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}],
    )
    db.commit()

    query = db.query(test_items).limit(2).offset(2)

    total = get_query_total(query)

    assert total == 5