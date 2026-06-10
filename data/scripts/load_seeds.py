import json
from pathlib import Path

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.place import Place


# Путь до сидов.
SEEDS_DIR = Path("data/seeds")


# Загружает города из cities.json.
# Idempotent: не создает дубли, если запись уже есть.
def load_cities(session: Session):
    path = SEEDS_DIR / "cities.json"

    if not path.exists():
        print("cities.json not found, skipping")
        return

    data = json.loads(path.read_text(encoding="utf-8"))

    for item in data:
        if session.get(City, item["id"]):
            continue

        session.add(City(**item))

    session.commit()
    print(f"Loaded cities: {len(data)}")


# Загружает места из всех файлов в places/.
# Idempotent: не создает дубли по id.
def load_places(session: Session):
    places_dir = SEEDS_DIR / "places"

    if not places_dir.exists():
        print("places directory not found, skipping")
        return

    total = 0

    for path in places_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))

        for item in data:
            if session.get(Place, item["id"]):
                continue

            # Убираем служебные поля перед записью в БД.
            item.pop("_needs_review", None)

            session.add(Place(**item))
            total += 1

    session.commit()
    print(f"Loaded places: {total}")


# Главная функция загрузки сидов.
def main():
    session = SessionLocal()

    try:
        load_cities(session)
        load_places(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()