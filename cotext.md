================================================================================
CITY GO — MASTER ENGINEERING CONTEXT
FULL PROJECT IMPORT CONTEXT FOR CODE AGENT
================================================================================

PROJECT NAME
City Go

PROJECT TYPE
Web-first AI city guide / travel recommendation platform.

HIGH-LEVEL PRODUCT IDEA
City Go помогает пользователю быстро получать персональные рекомендации мест
в городе и строить маршруты.

Primary surfaces:
- Web app (main product)
- Telegram Bot MVP (lite conversational layer)
- future mobile apps

Architecture principle:
ALL clients are thin clients over ONE backend source of truth.

No duplicated business logic across clients.

================================================================================
CURRENT ENGINEERING STATE
================================================================================

Backend stack:
- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- PostGIS
- Alembic
- Pydantic v2
- pytest
- unittest

Project structure (important):
app/
  api/
  routers/
  services/
  schemas/
  models/
  db/
  core/
  tests/
  docs/

Main app:
main.py

FastAPI app already exists.

================================================================================
MAIN ACTIVE DOMAIN: RECOMMENDATION PIPELINE
================================================================================

Main new endpoint:
POST /recommendations/route

Purpose:
Build recommendation route dynamically from candidate places.

This is NEW architecture.

OLD itinerary API still exists in parallel.

DO NOT confuse them.

OLD:
- routers/itinerary.py
- schemas/itinerary.py
- schemas/itinerary_replan.py

NEW:
- routers/recommendations.py
- schemas/recommendation_route.py
- services/* recommendation pipeline

OLD itinerary is NOT source of truth for new pipeline.

================================================================================
NEW RECOMMENDATION PIPELINE ARCHITECTURE
================================================================================

Current logical flow:

STEP 1
Context merge

service:
services/context_merge_service.py

input:
RequestContext

output:
MergedContext

Responsibilities:
- normalize request context
- defaults
- budget
- pace
- visiting mode
- effective time budget
- radius
- stop count

---

STEP 2
Candidate retrieval

service:
candidate retrieval DB service

Responsibilities:
- query DB
- geospatial filtering
- retrieve candidate places

Output:
List[Place]

DB smoke already exists.

---

STEP 2.5
Validation layer

service:
services/place_validation_service.py

Purpose:
validate raw place data quality

Function:
validate_place(place)

returns:
{
  "is_valid": bool,
  "issues": list[str]
}

Current validation rules:

lat/lng:
- missing
- invalid type
- out of range

opening_hours:
- invalid type
- day invalid
- unknown key
- time not string
- empty time string
- unparseable time

average_visit_duration_minutes:
- invalid type
- non-positive

category:
- empty

price_level:
- invalid type
- out of range

Important:
validation DOES NOT filter candidates.

Pipeline behavior:
after retrieval:
place.validation = validate_place(place)

---

STEP 3
Hard filters

service:
services/hard_filters_service.py

Purpose:
exclude impossible candidates

Examples:
- avoided categories
- excluded places
etc

---

STEP 4
Soft scoring

service:
services/scoring_service.py

Purpose:
rank candidates

Current scoring axes:
- interest
- distance
- context
- popularity (budget fit)
- novelty
- data_quality

data_quality:
reads place.validation["issues"]

Important:
data_quality affects ranking only.
NOT hard exclusion.

Current behavior:
clean place > dirty place
multiple issues > single issue

---

STEP 5
Route assembly

service:
services/route_assembly_service.py

Purpose:
build route sequence

Key objects:
ScoredPlace
RoutePoint

RoutePoint currently contains:
- place_id
- lat
- lng
- score
- category
- visit_minutes
- opening_hours
- validation

validation was intentionally propagated downstream.

---

STEP 6
Time-aware enrichment

service:
time-aware service

Purpose:
time simulation

adds:
- estimated_walk_minutes
- estimated_arrival_time
- estimated_departure_time
- time_status
- time_warning

Known statuses:
- ok
- HOURS_UNKNOWN
- CLOSES_DURING_VISIT
etc

---

STEP 7
Finalize

service:
services/route_finalize_service.py

Purpose:
produce FinalRoute

FinalRoute contains:
- route_id
- points
- total_minutes
- total_places
- estimated_distance
- total_estimated_minutes
- estimated_end_time
- has_warnings
- warning_count
- places_with_warnings
- warnings

Warning aggregation:

Time-aware:
time_status != ok
-> places_with_warnings

Validation:
ONLY visit_duration issues
-> route-level warnings

Current warning text:
"Для некоторых мест использовано приблизительное время визита."

Important:
opening_hours warnings are NOT duplicated here
because time-aware already covers that.

Critical invalid lat/lng should NOT surface to client warnings.

---

STEP 8
Explainability

service:
services/explainability_service.py

Purpose:
human-readable explanation

Consumes:
FinalRoute

Important:
Explainability reads:
- score breakdown
- warnings

No direct validation logic should be duplicated there.

================================================================================
HTTP LAYER
================================================================================

Router:
routers/recommendations.py

Endpoint:
POST /recommendations/route

Flow:
HTTP payload
-> RecommendationRouteRequest
-> RequestContext
-> RouteBuilderService.build_route(...)
-> ExplainabilityService.build_route_explanation(...)
-> RecommendationRouteResponse

Serialization:
datetime -> ISO strings

Source of truth schemas:
schemas/recommendation_route.py

Current response contains:
- route_id
- total_places
- total_minutes
- total_estimated_minutes
- estimated_distance
- estimated_end_time
- has_warnings
- warning_count
- places_with_warnings
- warnings
- points
- explanation

================================================================================
TESTING STATUS
================================================================================

GREEN:

tests/test_recommendations_route_router.py
Purpose:
HTTP smoke with mocks

---

tests/test_route_builder_pipeline_smoke.py
Purpose:
pipeline smoke

---

tests/test_scoring_service.py
Purpose:
scoring unit tests

---

tests/test_route_finalize_service.py
Purpose:
finalize unit tests

---

tests/test_place_validation_service.py
Purpose:
validation tests

---

tests/test_candidate_retrieval_db_smoke.py
Purpose:
DB smoke

---

tests/test_explainability_service.py
GREEN

---

tests/test_context_merge_service.py
GREEN

---

tests/test_hard_filters_service.py
GREEN

---

tests/test_route_assembly_service.py
GREEN

---

tests/test_time_aware_service.py
GREEN

================================================================================
INTEGRATION TEST STATUS
================================================================================

File:
tests/test_recommendations_route_integration.py

Purpose:
REAL end-to-end test

NO mocks:
- no RouteBuilder mock
- no Explainability mock
- no fake DB

Uses:
main.app
real DB
real pipeline

Activation:
RUN_RECOMMENDATIONS_INTEGRATION=1

Current result:
FAILS

Error:
SQLAlchemy InvalidRequestError

Root cause:
ORM relationship misconfiguration between City and Place

Specifically:
SQLAlchemy cannot determine join condition for:
City.places

Likely issue:
missing or broken:
- ForeignKey
- relationship()
- back_populates
- primaryjoin

This is current highest priority blocker.

IMPORTANT:
Do NOT hack integration tests around it.

Fix ORM root cause.

================================================================================
CURRENT IMMEDIATE TASK
================================================================================

Fix ORM mapping:
City <-> Place

Investigate:
- models/city.py
- models/place.py
- related Alembic migrations
- actual DB schema

Goal:
RUN_RECOMMENDATIONS_INTEGRATION=1 python3.11 -m pytest tests/test_recommendations_route_integration.py -v

must become green.

Rules:
- minimal sufficient fix
- no hacks
- no touching warnings
- no touching router
- no bypassing ORM

================================================================================
ARCHITECTURAL PRINCIPLES
================================================================================

STRICT:

1.
One source of truth backend.

2.
Clients thin.
No duplicated recommendation logic.

3.
Pipeline responsibilities separated by layer.

4.
No business logic in router.

5.
Validation != filtering.

6.
Scoring != hard exclusion.

7.
Finalize aggregates route summary.

8.
Explainability consumes finalized route.
Not duplicate upstream logic.

9.
Minimal sufficient fixes.
No opportunistic refactors.

10.
If fixing one layer:
DO NOT redesign adjacent layers unless explicitly requested.

================================================================================
WORKING STYLE EXPECTATIONS
================================================================================

Critical.

Output format expected:

ONE RESPONSE = ONE FILE

Format:
UPDATED FILE
path/to/file.py
<full file>

No diff.
No snippets.
No “replace this”.
No partial edits.

When task completes:
always provide git commit message.

Commit style:
fix:
feat:
test:
docs:
refactor:

Examples:
fix: align city place ORM relationship
feat: surface validation warnings in finalized route
test: cover route-level validation warnings
docs: sync backend file map with validation warning flow

================================================================================
WHAT NOT TO DO
================================================================================

DO NOT:
- rewrite architecture without request
- merge old itinerary with new recommendation pipeline
- add hacky mocks to integration
- duplicate warnings logic
- duplicate validation logic
- bypass ORM issue by disabling relationships
- change tests to hide failures
- invent schema fields not backed by real architecture

================================================================================
DOCUMENTATION
================================================================================

Architecture docs maintained:
docs/architecture/backend_file_map.md

This file is treated as working architecture registry.

When architecture changes:
update docs too.

Then provide commit message.

================================================================================
NEXT PRIORITY AFTER ORM FIX
================================================================================

After integration becomes green:

likely next sequence:

1.
ORM fix

2.
green integration verification

3.
debug / diagnostics visibility
OR
profile/personalization layer

depending on architectural decision

BUT DO NOT START NEXT STEP AUTOMATICALLY.

Wait for explicit instruction.

================================================================================
END OF CONTEXT
================================================================================================================================================================
CITY GO — MASTER ENGINEERING CONTEXT
FULL PROJECT IMPORT CONTEXT FOR CODE AGENT
================================================================================

PROJECT NAME
City Go

PROJECT TYPE
Web-first AI city guide / travel recommendation platform.

HIGH-LEVEL PRODUCT IDEA
City Go помогает пользователю быстро получать персональные рекомендации мест
в городе и строить маршруты.

Primary surfaces:
- Web app (main product)
- Telegram Bot MVP (lite conversational layer)
- future mobile apps

Architecture principle:
ALL clients are thin clients over ONE backend source of truth.

No duplicated business logic across clients.

================================================================================
CURRENT ENGINEERING STATE
================================================================================

Backend stack:
- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- PostGIS
- Alembic
- Pydantic v2
- pytest
- unittest

Project structure (important):
app/
  api/
  routers/
  services/
  schemas/
  models/
  db/
  core/
  tests/
  docs/

Main app:
main.py

FastAPI app already exists.

================================================================================
MAIN ACTIVE DOMAIN: RECOMMENDATION PIPELINE
================================================================================

Main new endpoint:
POST /recommendations/route

Purpose:
Build recommendation route dynamically from candidate places.

This is NEW architecture.

OLD itinerary API still exists in parallel.

DO NOT confuse them.

OLD:
- routers/itinerary.py
- schemas/itinerary.py
- schemas/itinerary_replan.py

NEW:
- routers/recommendations.py
- schemas/recommendation_route.py
- services/* recommendation pipeline

OLD itinerary is NOT source of truth for new pipeline.

================================================================================
NEW RECOMMENDATION PIPELINE ARCHITECTURE
================================================================================

Current logical flow:

STEP 1
Context merge

service:
services/context_merge_service.py

input:
RequestContext

output:
MergedContext

Responsibilities:
- normalize request context
- defaults
- budget
- pace
- visiting mode
- effective time budget
- radius
- stop count

---

STEP 2
Candidate retrieval

service:
candidate retrieval DB service

Responsibilities:
- query DB
- geospatial filtering
- retrieve candidate places

Output:
List[Place]

DB smoke already exists.

---

STEP 2.5
Validation layer

service:
services/place_validation_service.py

Purpose:
validate raw place data quality

Function:
validate_place(place)

returns:
{
  "is_valid": bool,
  "issues": list[str]
}

Current validation rules:

lat/lng:
- missing
- invalid type
- out of range

opening_hours:
- invalid type
- day invalid
- unknown key
- time not string
- empty time string
- unparseable time

average_visit_duration_minutes:
- invalid type
- non-positive

category:
- empty

price_level:
- invalid type
- out of range

Important:
validation DOES NOT filter candidates.

Pipeline behavior:
after retrieval:
place.validation = validate_place(place)

---

STEP 3
Hard filters

service:
services/hard_filters_service.py

Purpose:
exclude impossible candidates

Examples:
- avoided categories
- excluded places
etc

---

STEP 4
Soft scoring

service:
services/scoring_service.py

Purpose:
rank candidates

Current scoring axes:
- interest
- distance
- context
- popularity (budget fit)
- novelty
- data_quality

data_quality:
reads place.validation["issues"]

Important:
data_quality affects ranking only.
NOT hard exclusion.

Current behavior:
clean place > dirty place
multiple issues > single issue

---

STEP 5
Route assembly

service:
services/route_assembly_service.py

Purpose:
build route sequence

Key objects:
ScoredPlace
RoutePoint

RoutePoint currently contains:
- place_id
- lat
- lng
- score
- category
- visit_minutes
- opening_hours
- validation

validation was intentionally propagated downstream.

---

STEP 6
Time-aware enrichment

service:
time-aware service

Purpose:
time simulation

adds:
- estimated_walk_minutes
- estimated_arrival_time
- estimated_departure_time
- time_status
- time_warning

Known statuses:
- ok
- HOURS_UNKNOWN
- CLOSES_DURING_VISIT
etc

---

STEP 7
Finalize

service:
services/route_finalize_service.py

Purpose:
produce FinalRoute

FinalRoute contains:
- route_id
- points
- total_minutes
- total_places
- estimated_distance
- total_estimated_minutes
- estimated_end_time
- has_warnings
- warning_count
- places_with_warnings
- warnings

Warning aggregation:

Time-aware:
time_status != ok
-> places_with_warnings

Validation:
ONLY visit_duration issues
-> route-level warnings

Current warning text:
"Для некоторых мест использовано приблизительное время визита."

Important:
opening_hours warnings are NOT duplicated here
because time-aware already covers that.

Critical invalid lat/lng should NOT surface to client warnings.

---

STEP 8
Explainability

service:
services/explainability_service.py

Purpose:
human-readable explanation

Consumes:
FinalRoute

Important:
Explainability reads:
- score breakdown
- warnings

No direct validation logic should be duplicated there.

================================================================================
HTTP LAYER
================================================================================

Router:
routers/recommendations.py

Endpoint:
POST /recommendations/route

Flow:
HTTP payload
-> RecommendationRouteRequest
-> RequestContext
-> RouteBuilderService.build_route(...)
-> ExplainabilityService.build_route_explanation(...)
-> RecommendationRouteResponse

Serialization:
datetime -> ISO strings

Source of truth schemas:
schemas/recommendation_route.py

Current response contains:
- route_id
- total_places
- total_minutes
- total_estimated_minutes
- estimated_distance
- estimated_end_time
- has_warnings
- warning_count
- places_with_warnings
- warnings
- points
- explanation

================================================================================
TESTING STATUS
================================================================================

GREEN:

tests/test_recommendations_route_router.py
Purpose:
HTTP smoke with mocks

---

tests/test_route_builder_pipeline_smoke.py
Purpose:
pipeline smoke

---

tests/test_scoring_service.py
Purpose:
scoring unit tests

---

tests/test_route_finalize_service.py
Purpose:
finalize unit tests

---

tests/test_place_validation_service.py
Purpose:
validation tests

---

tests/test_candidate_retrieval_db_smoke.py
Purpose:
DB smoke

---

tests/test_explainability_service.py
GREEN

---

tests/test_context_merge_service.py
GREEN

---

tests/test_hard_filters_service.py
GREEN

---

tests/test_route_assembly_service.py
GREEN

---

tests/test_time_aware_service.py
GREEN

================================================================================
INTEGRATION TEST STATUS
================================================================================

File:
tests/test_recommendations_route_integration.py

Purpose:
REAL end-to-end test

NO mocks:
- no RouteBuilder mock
- no Explainability mock
- no fake DB

Uses:
main.app
real DB
real pipeline

Activation:
RUN_RECOMMENDATIONS_INTEGRATION=1

Current result:
FAILS

Error:
SQLAlchemy InvalidRequestError

Root cause:
ORM relationship misconfiguration between City and Place

Specifically:
SQLAlchemy cannot determine join condition for:
City.places

Likely issue:
missing or broken:
- ForeignKey
- relationship()
- back_populates
- primaryjoin

This is current highest priority blocker.

IMPORTANT:
Do NOT hack integration tests around it.

Fix ORM root cause.

================================================================================
CURRENT IMMEDIATE TASK
================================================================================

Fix ORM mapping:
City <-> Place

Investigate:
- models/city.py
- models/place.py
- related Alembic migrations
- actual DB schema

Goal:
RUN_RECOMMENDATIONS_INTEGRATION=1 python3.11 -m pytest tests/test_recommendations_route_integration.py -v

must become green.

Rules:
- minimal sufficient fix
- no hacks
- no touching warnings
- no touching router
- no bypassing ORM

================================================================================
ARCHITECTURAL PRINCIPLES
================================================================================

STRICT:

1.
One source of truth backend.

2.
Clients thin.
No duplicated recommendation logic.

3.
Pipeline responsibilities separated by layer.

4.
No business logic in router.

5.
Validation != filtering.

6.
Scoring != hard exclusion.

7.
Finalize aggregates route summary.

8.
Explainability consumes finalized route.
Not duplicate upstream logic.

9.
Minimal sufficient fixes.
No opportunistic refactors.

10.
If fixing one layer:
DO NOT redesign adjacent layers unless explicitly requested.

================================================================================
WORKING STYLE EXPECTATIONS
================================================================================

Critical.

Output format expected:

ONE RESPONSE = ONE FILE

Format:
UPDATED FILE
path/to/file.py
<full file>

No diff.
No snippets.
No “replace this”.
No partial edits.

When task completes:
always provide git commit message.

Commit style:
fix:
feat:
test:
docs:
refactor:

Examples:
fix: align city place ORM relationship
feat: surface validation warnings in finalized route
test: cover route-level validation warnings
docs: sync backend file map with validation warning flow

================================================================================
WHAT NOT TO DO
================================================================================

DO NOT:
- rewrite architecture without request
- merge old itinerary with new recommendation pipeline
- add hacky mocks to integration
- duplicate warnings logic
- duplicate validation logic
- bypass ORM issue by disabling relationships
- change tests to hide failures
- invent schema fields not backed by real architecture

================================================================================
DOCUMENTATION
================================================================================

Architecture docs maintained:
docs/architecture/backend_file_map.md

This file is treated as working architecture registry.

When architecture changes:
update docs too.

Then provide commit message.

================================================================================
NEXT PRIORITY AFTER ORM FIX
================================================================================

After integration becomes green:

likely next sequence:

1.
ORM fix

2.
green integration verification

3.
debug / diagnostics visibility
OR
profile/personalization layer

depending on architectural decision

BUT DO NOT START NEXT STEP AUTOMATICALLY.

Wait for explicit instruction.

================================================================================
END OF CONTEXT
================================================================================