"""Build enriched.csv from export.csv for a place enrichment batch."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

PREFIXES = (
    "Кафе:", "Еда:", "Культура:", "Музей:", "Прогулка:", "Парк:",
    "Пляж:", "Море:", "Достопримечательность:", "Семья:", "Тихо:",
)
NO_ADDR = {"", "Адрес не указан", "Адрес уточняется"}
BANNED = re.compile(r"seed|osm|import|проверки|требует проверки|обновлено", re.I)
CUISINE = {"cafe": "кафе", "food": "еда"}


def _needs_rewrite(text: str) -> bool:
    t = text.strip()
    return not t or t.startswith(PREFIXES) or bool(BANNED.search(t))


def _describe(title: str, city: str, category: str, current: str) -> str:
    if not _needs_rewrite(current):
        return current.strip()
    q = f"«{title}»"
    templates = {
        "cafe": f"Кафе {q} в {city} — место для кофе, перекуса или короткой остановки в маршруте.",
        "food": f"Заведение {q} в {city} подойдёт для остановки на еду во время прогулки.",
        "museum": f"{q} в {city} — музейная точка для спокойного визита в культурном маршруте.",
        "culture": f"{q} — культурно-историческая точка в {city} для спокойной остановки в маршруте.",
        "walk": f"Прогулочная точка {q} в {city} подойдёт для спокойного маршрута и короткой остановки.",
        "park": f"Парк {q} в {city} — зелёная зона для отдыха и прогулки в маршруте.",
        "viewpoint": f"Смотровая точка {q} в {city} — место для короткой остановки с видом на окрестности.",
    }
    return templates.get(category, f"{q} в {city} — точка для короткой остановки в городском маршруте.")


def _enrich_row(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    addr = (row.get("current_address") or "").strip()
    has_addr = addr not in NO_ADDR
    out["suggested_short_description"] = _describe(
        row.get("title", ""), row.get("city_name", ""), row.get("category", ""),
        row.get("current_short_description") or "",
    )
    out["suggested_address"] = addr if has_addr else ""
    out["suggested_price_level"] = (row.get("current_price_level") or "").strip()
    out["suggested_cuisine"] = CUISINE.get(row.get("category", ""), "")
    out["suggested_source_url"] = row.get("source_url") or ""
    out["suggested_data_source"] = "ai_description_from_export"
    out["suggested_confidence"] = "0.55" if has_addr else "0.45"
    base = "Описание подготовлено по названию, категории и городу"
    out["suggested_comment"] = (
        f"{base}; адрес скопирован из current_address."
        if has_addr else f"{base}; адрес не изменён."
    )
    return out


def fill_batch(batch_id: str, root: Path = Path("data/exports/place_enrichment/active")) -> int:
    export_path = root / batch_id / "export.csv"
    enriched_path = root / batch_id / "enriched.csv"
    rows = list(csv.DictReader(export_path.open(encoding="utf-8")))
    enriched = [_enrich_row(r) for r in rows]
    with enriched_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(enriched)
    return len(enriched)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-id", action="append", required=True)
    args = p.parse_args()
    for bid in args.batch_id:
        n = fill_batch(bid)
        print(f"{bid}: {n} rows -> enriched.csv")


if __name__ == "__main__":
    main()
