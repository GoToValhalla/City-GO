# Route Quality Gates — Stage 1

## Цель

Маршрутный слой не должен пропускать в маршруты служебные, мусорные и автоматически названные OSM-точки. Админка должна позволять быстро выбрать качественные места из большого набора и массово подтвердить их для маршрутов.

## Hard gates

Место не считается готовым для маршрутов, если:

- нет координат;
- координаты равны `0,0`;
- место выключено или не опубликовано;
- место скрыто из каталога;
- категория входит в запрещённые для маршрутов;
- название является auto-generated placeholder.

## Placeholder names

Следующие названия считаются fallback-заглушками, а не реальными названиями места:

- `Культурное место OSM ...`;
- `Место для прогулки OSM ...`;
- `Парк OSM ...`;
- `Пляж OSM ...`;
- `OSM node/way/relation ...`;
- `Unnamed`, `Unknown`, `Без названия`, `Место без названия`.

Для таких мест выставляется reason `placeholder_title`. Они не должны попадать в route candidates и не должны массово подтверждаться как high-quality места.

## Admin filters

Экран `/admin/routes/eligibility` поддерживает отбор по:

- готовности: all, route_ready, catalog_ready, high_quality, needs_fix, low_quality, placeholder;
- маршрутам: all, confirmed, not confirmed;
- quality bucket: high, medium, low;
- минимальному quality score;
- причине блокировки.

## Массовая публикация

Для безопасного массового подтверждения:

1. выбрать город;
2. нажать `Показать высокое качество`;
3. проверить строки текущей страницы;
4. выбрать видимые строки;
5. нажать `Подтвердить для маршрутов`.

Массовое действие применяется только к выбранным строкам текущей страницы.

## Route editing regression

После добавления точки в маршрут должны пересчитываться:

- revision;
- total_places;
- total_estimated_minutes;
- total_walk_distance_meters;
- time_breakdown;
- category_distribution;
- points для карты.

Frontend дополнительно перемонтирует route result panel по ключу route_id/revision/points/time, чтобы summary и карта не оставались в старом состоянии.
