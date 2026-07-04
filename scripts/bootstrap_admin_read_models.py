from __future__ import annotations

from db.session import engine
from models.admin_read_snapshot import AdminOverviewSnapshot, BacklogQueueSnapshot, CityQualitySnapshot


def bootstrap_admin_read_models() -> dict[str, object]:
    AdminOverviewSnapshot.__table__.create(bind=engine, checkfirst=True)
    CityQualitySnapshot.__table__.create(bind=engine, checkfirst=True)
    BacklogQueueSnapshot.__table__.create(bind=engine, checkfirst=True)
    return {
        "status": "ok",
        "tables": [
            AdminOverviewSnapshot.__tablename__,
            CityQualitySnapshot.__tablename__,
            BacklogQueueSnapshot.__tablename__,
        ],
    }


def main() -> None:
    result = bootstrap_admin_read_models()
    print(result)


if __name__ == "__main__":
    main()
