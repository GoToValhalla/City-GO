import json
from collections import Counter
from pathlib import Path


# Анализирует итоговый seed-файл по Зеленоградску:
# - общее число мест
# - сколько требует ревью
# - распределение по категориям
# - сколько мест без opening_hours
# - сколько мест с price_level = 0
PLACES_PATH = Path("data/seeds/places/zelenogradsk.json")


def main():
    data = json.loads(PLACES_PATH.read_text(encoding="utf-8"))

    total = len(data)
    needs_review = sum(1 for place in data if place.get("_needs_review"))
    no_opening_hours = sum(1 for place in data if not place.get("opening_hours"))
    zero_price_level = sum(1 for place in data if place.get("price_level", 0) == 0)

    categories = Counter(place.get("category", "unknown") for place in data)

    print(f"Total places: {total}")
    print(f"Needs review: {needs_review}")
    print(f"No opening_hours: {no_opening_hours}")
    print(f"Price level = 0: {zero_price_level}")

    print("\n--- Categories ---")
    for category, count in sorted(categories.items()):
        print(f"{category}: {count}")


if __name__ == "__main__":
    main()
