# Route Navigation Layer

## Цель

Каждая точка маршрута должна быть пригодна для навигации даже при отсутствии точного адреса.

---

## Навигационные поля в route response

Каждая точка маршрута (`UserRoutePoint`, `RecommendationRoutePointResponse`) содержит:

| Поле | Тип | Описание |
|------|-----|----------|
| `display_location` | `string` | Адрес или `"Адрес уточняется · открыть на карте"` |
| `has_address` | `bool` | `true` если адрес реальный |
| `navigation_url_google` | `string` | Google Maps URL |
| `navigation_url_yandex` | `string` | Яндекс Карты URL |
| `navigation_url_osm` | `string` | OpenStreetMap URL |
| `estimated_distance_meters` | `int \| null` | Примерная дистанция пешком, вычисленная из `estimated_walk_minutes` |
| `estimated_walk_minutes` | `int \| null` | Время пешком до точки от предыдущей (уже существовало) |

---

## Как пользователь понимает куда идти

1. `display_location` — всегда непустой: либо реальный адрес, либо fallback-текст.
2. Три кнопки навигации: Google Maps, Яндекс Карты, OSM — всегда доступны если точка в маршруте.
3. Если адреса нет — текст `display_location` выводится серым цветом (`route-address-muted`).
4. Маршрут **не блокируется** из-за отсутствия адреса.

---

## Fallback без адреса

```
address пустой/плейсхолдер/generic для заведения → display_location = "Адрес уточняется · открыть на карте"
                     has_address = false
                     navigation URLs рабочие (используют lat/lng)
```

Плейсхолдеры, которые не считаются реальным адресом:
`"адрес уточняется"`, `"адрес не указан"`, `"нет адреса"`, `"unknown"`, `"-"`

---

## Navigation URL-шаблоны

| Провайдер | URL-шаблон |
|-----------|------------|
| Google Maps | `https://www.google.com/maps/search/?api=1&query={lat},{lng}` |
| Яндекс Карты | `https://yandex.com/maps/?pt={lng},{lat}&z=17&l=map` |
| OpenStreetMap | `https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}` |

Реализация: `services/route_navigation_service.py`

---

## Estimated distance: не turn-by-turn

Дистанция рассчитывается через haversine с городской поправкой:

```python
# route_geometry.py
WALK_METERS_PER_MIN = 75.0   # средняя скорость пешехода
URBAN_FACTOR = 1.25           # городская поправка
distance_meters = estimated_walk_minutes * 75 / 1.25
```

Поле называется `estimated_distance_meters` — это явное указание на приблизительность.
**Turn-by-turn navigation не реализован.**

---

## Telegram

Telegram-бот добавляет к каждой точке маршрута адрес или координаты и HTML-ссылку на Google Maps:

```
1. Пушкинский парк · 📍 ул. Пушкина, 10 · 🗺 Google Maps · 09:00-09:30 · 30 мин · 5 мин пешком
```

---

## Address Backfill

```bash
# dry-run — показывает что будет обновлено
python data/scripts/backfill_missing_place_addresses.py --city zelenogradsk --limit 50

# применить изменения
python data/scripts/backfill_missing_place_addresses.py --city zelenogradsk --limit 50 --apply

# все города
python data/scripts/backfill_missing_place_addresses.py --limit 100 --apply
```

Скрипт **не перезаписывает реальный адрес**: `_needs_address()` пропускает место если у него непустой и не-плейсхолдерный адрес.

---

## Будущие задачи (out of scope)

- Полноценный routing API (OSRM / Valhalla / GraphHopper) для маршрута по дорогам
- Turn-by-turn навигация
- Deep-link для открытия нативного приложения карт на мобильных
- Режим велосипед / транспорт
# Location lifecycle

Активная навигация использует общий frontend location provider. Browser
`watchPosition` запускается только после пользовательского старта маршрута и
очищается при завершении, reset, смене маршрута и unmount. Telegram
`LocationManager` остаётся one-shot и обновляется кнопкой вручную.
