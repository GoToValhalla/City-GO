"""One-off: fill enriched.csv for khanty-mansiysk batch 20260607_150242."""
from __future__ import annotations

import csv
from pathlib import Path

BATCH = Path(
    "data/exports/place_enrichment/active/"
    "place_enrichment_khanty-mansiysk_20260607_150242"
)
NO_ADDR = "Адрес не указан"

DESCRIPTIONS: dict[str, str] = {
    "khanty-mansiysk-culture-югра-node-435174941": (
        "Культурная точка «Югра» в Ханты-Мансийске. "
        "Подходит для короткой остановки в городском маршруте."
    ),
    "khanty-mansiysk-culture-мемориал-вов-node-436059308": (
        "Мемориал ВОВ в Ханты-Мансийске — место для спокойной паузы. "
        "Удобная точка мемориального маршрута в центре города."
    ),
    "khanty-mansiysk-culture-t-34-node-595628270": (
        "Экспозиция танка T-34 в Ханты-Мансийске — памятник военной техники "
        "для короткой остановки рядом с мемориальной зоной."
    ),
    "khanty-mansiysk-food-югра-node-1132104623": (
        "Заведение «Югра» в Ханты-Мансийске — точка общепита "
        "для обеда или перекуса по пути."
    ),
    "khanty-mansiysk-cafe-ассорти-node-1137747707": (
        "Кафе «Ассорти» на улице Мира — место для кофе и перекуса "
        "в центральной части Ханты-Мансийска."
    ),
    "khanty-mansiysk-food-панорама-node-1165414774": (
        "Заведение «Панорама» в Ханты-Мансийске для остановки "
        "и приёма пищи в маршруте."
    ),
    "khanty-mansiysk-food-фристайл-node-1165415231": (
        "Заведение «Фристайл» в Ханты-Мансийске — точка общепита "
        "для обеда или лёгкого перекуса."
    ),
    "khanty-mansiysk-food-на-семи-холмах-node-1165417143": (
        "Ресторан «На семи холмах» в Ханты-Мансийске — остановка "
        "для обеда или перекуса в городском маршруте."
    ),
    "khanty-mansiysk-cafe-театр-node-1184203389": (
        "Кафе «Театр» в Ханты-Мансийске — удобная остановка на кофе или перекус."
    ),
    "khanty-mansiysk-cafe-goodfood-node-1217177666": (
        "Кафе Goodfood в Ханты-Мансийске для короткой остановки "
        "на кофе или лёгкий перекус."
    ),
    "khanty-mansiysk-cafe-мангал-house-node-1221698825": (
        "Кафе «Мангал & House» в Ханты-Мансийске — место "
        "для остановки и простого перекуса."
    ),
    "khanty-mansiysk-cafe-назымчанка-node-1223918008": (
        "Кафе «Назымчанка» в Ханты-Мансийске для короткой остановки "
        "на кофе или перекус."
    ),
    "khanty-mansiysk-museum-этнографический-музей-под-открытым-небом-торум-маа-node-1252537020": (
        "Этнографический музей под открытым небом «Торум Маа» на улице Собянина "
        "показывает традиции народов Югры. Подходит для культурного маршрута."
    ),
    "khanty-mansiysk-food-посейдон-node-1254906391": (
        "Заведение «Посейдон» в Ханты-Мансийске — точка общепита "
        "для остановки и приёма пищи."
    ),
    "khanty-mansiysk-cafe-две-реки-node-1254914935": (
        "Кафе «Две реки» в Ханты-Мансийске для короткой остановки на кофе или перекус."
    ),
    "khanty-mansiysk-cafe-изумрудный-город-node-1255586251": (
        "Кафе «Изумрудный город» в Ханты-Мансийске — место для кофе "
        "и перекуса в городском маршруте."
    ),
    "khanty-mansiysk-cafe-сладкоежка-node-1255620338": (
        "Кафе «Сладкоежка» в Ханты-Мансийске — подходит для кофе и сладкого перекуса."
    ),
    "khanty-mansiysk-cafe-кристалл-node-1256776795": (
        "Кафе «Кристалл» в Ханты-Мансийске для короткой остановки на кофе или перекус."
    ),
    "khanty-mansiysk-food-старый-двор-node-1260434748": (
        "Заведение «Старый двор» в Ханты-Мансийске — точка общепита для обеда в маршруте."
    ),
    "khanty-mansiysk-cafe-венское-кафе-node-1260512835": (
        "Кафе «Венское кафе» в Ханты-Мансийске — спокойная остановка для кофе и десерта."
    ),
    "khanty-mansiysk-food-амадеус-node-1260512837": (
        "Заведение «Амадеус» в Ханты-Мансийске для обеда или перекуса по пути."
    ),
    "khanty-mansiysk-cafe-олимп-node-1260558434": (
        "Кафе «Олимп» в Ханты-Мансийске — удобная точка для кофе или лёгкого перекуса."
    ),
    "khanty-mansiysk-cafe-traveler-s-caffee-node-1261806389": (
        "Кафе Traveler's Caffee в Ханты-Мансийске для короткой остановки "
        "на кофе или перекус."
    ),
    "khanty-mansiysk-food-таежный-тупик-node-1270304848": (
        "Заведение «Таежный тупик» в Ханты-Мансийске — точка общепита "
        "для остановки и приёма пищи."
    ),
    "khanty-mansiysk-food-chester-pub-node-1270326077": (
        "Chester Pub в Ханты-Мансийске — заведение формата паб "
        "для остановки и перекуса в маршруте."
    ),
    "khanty-mansiysk-museum-музей-геологии-нефти-и-газа-node-1271675395": (
        "Музей геологии, нефти и газа в Ханты-Мансийске знакомит "
        "с историей освоения нефтегазового региона. Подходит для культурного маршрута."
    ),
    "khanty-mansiysk-cafe-луч-node-1271695854": (
        "Кафе «Луч» в Ханты-Мансийске — остановка на кофе или перекус."
    ),
    "khanty-mansiysk-museum-музей-природы-и-человека-node-1271675402": (
        "Музей природы и человека в Ханты-Мансийске рассказывает о природе "
        "и культуре Югры. Удобная точка для спокойного музейного визита."
    ),
    "khanty-mansiysk-cafe-под-интегралом-node-1271695855": (
        "Кафе «Под интегралом» в Ханты-Мансийске для короткой остановки на кофе или перекус."
    ),
    "khanty-mansiysk-cafe-аракс-node-1271695857": (
        "Кафе «Аракс» в Ханты-Мансийске — место для кофе и перекуса в центре города."
    ),
}

CUISINE: dict[str, str] = {
    "cafe": "кофе и перекус",
    "food": "общепит",
    "culture": "культура",
    "museum": "музей",
}


def _comment(has_addr: bool) -> str:
    parts = [
        "Описание подготовлено по названию, категории и городу; адрес не изменён.",
        "Текущее описание заменяет технический префикс импорта.",
    ]
    if has_addr:
        parts.append("Адрес перенесён из export (current_address, источник OSM).")
    else:
        parts.append("Адрес не заполнен: нет подтверждённого источника.")
    return " ".join(parts)


def _enrich_row(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    slug = row["slug"]
    cat = row.get("category", "")
    addr = (row.get("current_address") or "").strip()
    has_addr = bool(addr and addr != NO_ADDR)

    out["suggested_short_description"] = DESCRIPTIONS[slug]
    out["suggested_price_level"] = row.get("current_price_level") or ""
    out["suggested_cuisine"] = CUISINE.get(cat, "")
    out["suggested_source_url"] = row.get("source_url") or ""
    out["suggested_data_source"] = "ai_description_from_export"
    out["suggested_confidence"] = "0.7" if has_addr else "0.45"
    out["suggested_comment"] = _comment(has_addr)
    out["suggested_address"] = addr if has_addr else ""
    return out


def main() -> None:
    export_path = BATCH / "export.csv"
    enriched_path = BATCH / "enriched.csv"
    with export_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fieldnames = rows[0].keys() if rows else []
    missing = [r["slug"] for r in rows if r["slug"] not in DESCRIPTIONS]
    if missing:
        raise SystemExit(f"Missing descriptions: {missing}")
    enriched = [_enrich_row(r) for r in rows]
    with enriched_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(enriched)
    print(f"Wrote {len(enriched)} rows -> {enriched_path}")


if __name__ == "__main__":
    main()
