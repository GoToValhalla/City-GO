import json
from pathlib import Path


# Проверяем итоговый seed-файл по Зеленоградску.
PLACES_PATH = Path("data/seeds/places/zelenogradsk.json")


# Минимальный обязательный набор полей для place.
REQUIRED_FIELDS = [
    "id",
    "city_id",
    "name",
    "category",
    "lat",
    "lng",
    "price_level",
    "average_visit_duration_minutes",
    "active",
]


# Валидирует places seed:
# - обязательные поля
# - дубли id
# - тип координат
def validate_places():
    data = json.loads(PLACES_PATH.read_text(encoding="utf-8"))

    ids = set()
    errors = []

    for index, place in enumerate(data):
        # Проверяем обязательные поля.
        for field in REQUIRED_FIELDS:
            if field not in place:
                errors.append(f"[{index}] missing field: {field}")

        # Проверяем дубли по id.
        place_id = place.get("id")
        if place_id:
            if place_id in ids:
                errors.append(f"duplicate id: {place_id}")
            ids.add(place_id)

        # Проверяем координаты.
        if not isinstance(place.get("lat"), (int, float)):
            errors.append(f"{place_id}: invalid lat")

        if not isinstance(place.get("lng"), (int, float)):
            errors.append(f"{place_id}: invalid lng")

    print(f"Total places: {len(data)}")
    print(f"Errors: {len(errors)}")

    # Печатаем первые ошибки, если они есть.
    if errors:
        print("\n--- ERRORS ---")
        for err in errors[:50]:
            print(err)


if __name__ == "__main__":
    validate_places()