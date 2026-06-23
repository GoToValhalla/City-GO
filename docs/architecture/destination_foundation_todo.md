# Destination Foundation TODO

Источник: архитектурный разбор City GO после выявления ограничения city-only модели для Алтая, Байкала, Карелии, национальных парков и больших туристических территорий.

## Главный вывод

Текущая модель `City -> Places` остается рабочей для компактных городов, но не масштабируется на туристические регионы. `City` не должен быть корневой сущностью Data Foundation. Корневой продуктовой сущностью должен стать `Destination`.

`City` нужно сохранить, но понизить до частного типа `Destination` с обратной совместимостью для текущих API, маршрутов, админки и импортов.

## Целевая модель

```text
Destination
- city
- natural_region
- national_park
- tourist_cluster
- route_corridor
- district
```

```text
Place
- физически независимая точка с координатами
- legacy city_id временно остается для обратной совместимости
- primary_destination_id добавляется как целевой контекст
- many-to-many связь с Destination через place_destinations
```

## Новые классы / таблицы, которые нужно создать

### Destination

TODO:
- создать модель `Destination`;
- поддержать типы `city`, `natural_region`, `national_park`, `tourist_cluster`, `route_corridor`, `district`;
- хранить `slug`, `name`, `type`, `parent_id`, `country_id`, `region_id`;
- хранить `center_lat`, `center_lng`, `bbox`, `boundary`, `osm_relation_id`;
- хранить `launch_status`, `is_active`, `is_published`, `is_searchable`;
- хранить `readiness_score`, `quality_status`, `tourist_tier`, `expected_places_count`;
- поддержать backward compatibility: каждый текущий `City` должен получить `Destination(type='city')`.

### DestinationCityMeta

TODO:
- создать таблицу для городских атрибутов, если `City` будет мигрировать в `Destination`;
- хранить population/class/timezone/legacy city fields;
- не ломать текущую таблицу `cities` на первом этапе.

### DestinationRelation / DestinationAncestor

TODO:
- создать связи между Destination;
- поддержать рекурсивную иерархию и materialized ancestors;
- поддержать `Baikal -> Olkhon`, `Altai -> Chuysky Tract`, `Golden Ring -> child cities`;
- учитывать, что строгая tree-иерархия недостаточна, потому что туристические кластеры могут пересекаться с административными зонами.

### PlaceDestination

TODO:
- создать many-to-many связь `Place <-> Destination`;
- поля: `place_id`, `destination_id`, `is_primary`, `assignment_type`, `confidence`, `source`;
- `assignment_type`: `legacy_city`, `spatial`, `manual`, `imported`, `route_corridor`;
- материализовать spatial membership, чтобы API не делал тяжелый `ST_Within` на каждый запрос.

### DestinationImportScope

TODO:
- заменить/расширить `CityImportScope`;
- scope должен принадлежать `destination_id`, а не только `city_id`;
- поддержать стратегии `single_bbox`, `osm_relation`, `tiled`, `manual_polygon`, `route_corridor`, `per_child`;
- поддержать разные профили импорта для городов и регионов;
- для больших регионов использовать tile/grid import, а не один огромный bbox.

### DestinationPublicationStatus

TODO:
- публикация должна работать не только на уровне города;
- поддержать staged publication: `tier1`, `tier2`, `tier3`, `unpublished`;
- Destination может стать публичным с топовым слоем мест, не дожидаясь проверки всех десятков тысяч объектов;
- место может быть опубликовано в одном Destination и скрыто в другом контексте.

### DestinationReadiness

TODO:
- readiness считать не только по городу, а по Destination и его scopes;
- отдельно считать coverage по адресам, фото, описаниям, категориям, route eligibility, мусору, дублям;
- поддержать readiness для регионов с большим количеством неготовых мест.

## Импорт регионов

TODO:
- не использовать один bbox для регионов уровня Алтай/Байкал/Карелия;
- поддержать Hub & Corridor ingestion:
  - хабы: населенные пункты, турбазы, поселки, точки входа;
  - коридоры: дороги, побережья, популярные маршруты;
  - природные POI: waterfall, peak, viewpoint, cave, attraction, historic, protected area;
- добавить import profiles:
  - `city_tourist`;
  - `nature_region`;
  - `national_park`;
  - `route_corridor`;
  - `tourist_cluster`;
- для природных регионов требовать более строгую релевантность: `name`, `tourism/historic/natural/leisure`, wikipedia/wikidata/website/photo приоритетом;
- utility-объекты (`parking`, `bench`, `toilet`, `pharmacy`, `atm`, `bus_stop`) не должны попадать в туристический каталог и маршруты, только в отдельный utility слой.

## Каталог и поиск

TODO:
- добавить `/destinations`;
- добавить каталог по `destination_slug`, не только по `city_slug`;
- `city_slug` оставить legacy alias;
- поиск должен сначала находить Destination (`Байкал`, `Алтай`, `Карелия`), потом места внутри выбранного Destination;
- поддержать фильтр по ancestor Destination: все места Байкала включая дочерние зоны;
- добавить full-text индекс по destinations и places.

## Маршруты

TODO:
- текущий Route Engine жестко фильтрует кандидатов по `City.slug == ctx.city_id`;
- добавить в route context `destination_id`, `destination_slug`, `destination_type`, `route_type`;
- поддержать типы маршрутов:
  - `city_walk`;
  - `area_walk`;
  - `region_drive`;
  - `multi_day`;
  - `route_corridor`;
  - `cluster_tour`;
- для city route можно оставить старый radius logic;
- для natural/region route использовать Destination/PlaceDestination membership, corridor buffer, travel mode и лимиты расстояния между точками;
- fallback должен расширять spatial scope, а не возвращаться к city-wide.

## Миграционный план

### Phase 0: TODO фиксация

- добавить TODO в текущие city/place/import/route/publication файлы;
- создать архитектурный документ и scaffold-классы без включения в runtime.

### Phase 1: Backward-compatible Destination Foundation

- создать `destinations`;
- создать `place_destinations`;
- для каждого текущего City создать `Destination(type='city')`;
- заполнить `Place.primary_destination_id` / `PlaceDestination` из текущего `city_id`;
- сохранить `city_id` и старые API;
- не трогать Route Engine как первый шаг.

### Phase 2: Destination Catalog

- добавить `/destinations`;
- добавить `/places?destination_slug=`;
- оставить `/places?city_slug=` как legacy mapping;
- добавить admin UI для Destination.

### Phase 3: Destination Import Scopes

- расширить import scopes от city к destination;
- добавить `osm_relation`, `manual_polygon`, `tiled`, `route_corridor`;
- первым пилотом брать не Алтай, а компактную территорию: Куршская коса / небольшой national park.

### Phase 4: Regional Publication

- staged publication;
- tier-based review;
- readiness по scopes;
- batch actions по кластерам.

### Phase 5: Route Engine V2

- route context по destination;
- multi-destination маршруты;
- corridor-based retrieval;
- travel mode aware routing.

## Принцип

Не превращать регион в fake city. Не создавать `city=baikal` или `city=altai`. Это повторит текущую архитектурную ошибку в большем масштабе.
