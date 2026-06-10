# Full city import run report

Generated: 2026-06-09T21:19:09.209525+00:00
Audit dir: `data/audit/full_city_import_run/local_20260609_194019`
Prod commit: `unknown`

## City snapshots (before → after)

| City | total | published | addr+ | photo+ | route_eligible | errors |
|------|------:|----------:|------:|-------:|---------------:|-------:|
| almaty | 0→1746 | 0→305 | 0→283 | 0→0 | 0→305 | 1 |
| yerevan | 0→2258 | 0→434 | 0→426 | 0→1 | 0→434 | 1 |
| zelenogradsk | 67→279 | 67→197 | 66→162 | 0→0 | 67→197 | 0 |
| kaliningrad | 1→1508 | 1→587 | 1→238 | 0→3 | 1→587 | 0 |
| kutaisi | 0→480 | 0→141 | 0→75 | 0→0 | 0→141 | 0 |
| rostov-on-don | 0→1145 | 0→438 | 0→159 | 0→1 | 0→438 | 0 |
| khanty-mansiysk | 145→397 | 145→147 | 140→105 | 1→1 | 145→147 | 0 |

## Pipeline deltas per city

- **almaty**: OSM created=1746, addresses+=55, photos+=0
- **yerevan**: OSM created=2258, addresses+=58, photos+=2
- **zelenogradsk**: OSM created=212, addresses+=66, photos+=0
- **kaliningrad**: OSM created=1507, addresses+=90, photos+=3
- **kutaisi**: OSM created=480, addresses+=87, photos+=0
- **rostov-on-don**: OSM created=1145, addresses+=88, photos+=1
- **khanty-mansiysk**: OSM created=252, addresses+=89, photos+=0

## Kaliningrad focus

- places_total=1508, published=587
- without_real_address=349
- category_counts={'useful': 338, 'food': 331, 'culture': 298, 'health': 212, 'cafe': 198, 'walk': 55, 'museum': 36, 'park': 36, 'viewpoint': 4}

## Suspicious category gaps

- zelenogradsk: {'park': 2, 'beach': 1}
- rostov-on-don: {'beach': 1}
- khanty-mansiysk: {'viewpoint': 2}
