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

    loaded = 0
    for item in data:
        payload = _city_payload(item)
        if session.query(City).filter(City.slug == payload["slug"]).first():
            continue

        session.add(City(**payload))
        loaded += 1

    session.commit()
    print(f"Loaded cities: {loaded}")


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


def _city_payload(item: dict[str, object]) -> dict[str, object]:
    slug = str(item.get("slug") or item.get("id") or "").strip()
    if not slug:
        raise ValueError("City seed requires slug or id")

    country = str(item.get("country") or "Россия")
    if country == "RU":
        country = "Россия"

    return {
        "slug": slug,
        "name": str(item.get("name") or slug),
        "region": item.get("region"),
        "country": country,
        "timezone": str(item.get("timezone") or "Europe/Moscow"),
        "center_lat": item.get("center_lat", item.get("lat")),
        "center_lng": item.get("center_lng", item.get("lng")),
        "launch_status": str(item.get("launch_status") or "published"),
        "is_active": bool(item.get("is_active", item.get("active", True))),
    }


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
