# City GO — User Journey v2

Date: 2026-07-02
Parent: CITYGO-149

## 1. First open

User opens Telegram Mini App or web.

States:

- app_loading;
- city_required;
- city_selected;
- unsupported_city;
- degraded_mode.

Success:

- user understands where to start;
- city can be selected;
- unsupported city has clear explanation.

## 2. City selection

User selects current city, searches city, or uses location.

Rules:

- if city is published, route modes are available;
- if city is in review, show limited preview only;
- if city is unsupported, offer future city request.

## 3. Route intent

User chooses one of four modes:

- quick route;
- category route;
- manual route;
- slot route.

Required outputs:

- estimated duration;
- route status;
- warnings if data quality is low.

## 4. Route build

System loads route candidates from routing projection.

States:

- requested;
- candidates_loaded;
- route_built;
- partial;
- empty;
- failed.

Failure reasons:

- not enough places;
- route budget too tight;
- stale projection;
- no route eligible candidates;
- city not published.

## 5. Route preview

User sees:

- route summary;
- map;
- list of places;
- total duration;
- warnings;
- replace/remove/add actions.

Success:

- user can start route;
- user can edit route;
- user can rebuild route.

## 6. Active route

States:

- active;
- paused;
- deviated;
- completed;
- abandoned;
- rebuilt.

Actions:

- mark visited;
- skip place;
- replace place;
- rebuild from current point;
- finish route.

## 7. Place details

User opens place card.

Must show:

- title;
- category;
- photo if approved;
- short description;
- address;
- opening hours if known;
- route relevance;
- warning if data quality is low.

## 8. Saved route

User can return to route if session exists.

Rules:

- restore route snapshot;
- warn if projection became stale;
- allow rebuild.

## 9. Admin city launch journey

Admin creates or selects destination.

Flow:

1. create destination;
2. configure import scopes;
3. run import;
4. inspect import results;
5. run enrichment;
6. review quality dashboard;
7. approve places;
8. publish destination;
9. rebuild projections;
10. run route smoke tests.

## 10. Admin review journey

Flow:

1. open review queue;
2. filter by city, quality gap, category, source;
3. inspect candidate evidence;
4. approve, reject, defer or escalate;
5. action writes ReviewDecision;
6. publication remains separate.

## 11. Admin emergency journey

Flow:

1. alert arrives;
2. admin opens health/admin page;
3. activates kill switch if needed;
4. hides or rolls back affected item;
5. reason and audit are required;
6. projections are rebuilt if public state changed.

## 12. Account lifecycle

Future flow:

- anonymous session;
- Telegram identity link;
- saved routes;
- preferences;
- export/delete account.
