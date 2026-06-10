import json
from pathlib import Path


PLACES_PATH = Path("data/seeds/places/zelenogradsk.json")


def main():
    data = json.loads(PLACES_PATH.read_text(encoding="utf-8"))

    total = len(data)
    needs_review = [place for place in data if place.get("_needs_review")]

    print(f"Total places: {total}")
    print(f"Needs review: {len(needs_review)}")

    if needs_review:
        print("\n--- FIRST 50 NEED REVIEW ---")
        for place in needs_review[:50]:
            print(
                f"{place.get('id')} | "
                f"{place.get('name')} | "
                f"{place.get('category')} | "
                f"price_level={place.get('price_level')} | "
                f"opening_hours={place.get('opening_hours')}"
            )


if __name__ == "__main__":
    main()
