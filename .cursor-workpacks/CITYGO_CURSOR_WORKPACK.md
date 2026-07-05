CITY GO — Cursor Workpack Master

Дата создания: 2026-07-05  
Последнее обновление: 2026-07-05  
Статус: рабочая мастер-страница для Cursor-контекста.  
Назначение: один copy-paste workpack для Cursor, который обновляется после утверждения архитектуры сайта, админки, Telegram/TMA и дизайн-баз.

Jira maintenance task: CITYGO-183 — Maintain Cursor Workpack Master

Важно: Cursor не имеет доступа к Confluence/Jira. Все ссылки на этой странице — для человека. Для Cursor источник должен быть локальным файлом .cursor-workpacks/CITYGO_CURSOR_WORKPACK.md, в который копируется полный текст этой страницы. Cursor не должен получать инструкцию “прочитай Confluence”. Он должен читать только локальный markdown-файл.

1. Как использовать

Когда работаешь у компьютера, скопируй весь текст этой страницы в локальный файл:

.cursor-workpacks/CITYGO_CURSOR_WORKPACK.md

Добавь в .gitignore:

.cursor-workpacks/
.cursor-local/
CITYGO_CURSOR_WORKPACK.md

После этого в Cursor написать:

Read .cursor-workpacks/CITYGO_CURSOR_WORKPACK.md first.
Do not open Confluence or Jira links; you do not have access to them.
Use only the local workpack content as the implementation context.
Do not implement anything outside the Current Cursor Task section.
Before editing, summarize what files you will touch and what tests you will run.

2. Human source links

Confluence remains the human source of truth. For Cursor, links are not executable context.

Approved specs:

Data Pipeline Control Plane v1.2 FINAL: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8028162/CITY+GO+Data+Pipeline+Control+Plane+v1.2+FINAL

User Web / Site Architecture v1: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8224770/CITY+GO+User+Web+Site+Architecture+v1

Admin Architecture v1: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8224793/CITY+GO+Admin+Architecture+v1

Telegram Bot / TMA Architecture v1: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8028218/CITY+GO+Telegram+Bot+TMA+Architecture+v1

User Web Visual Design v1: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8257538/CITY+GO+User+Web+Visual+Design+v1

Admin Visual Design v1: https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8290306/CITY+GO+Admin+Visual+Design+v1

Jira reminders:

Telegram/TMA Visual Design v1 follow-up task: CITYGO-184

3. Global Cursor rules

Repository:

GoToValhalla/City-GO

Default branch:

main

Hard rules:

Do not change auth unless explicitly instructed.

Do not change deploy workflows unless explicitly instructed.

Do not change CI triggers unless explicitly instructed.

Do not add migrations unless the current workpack explicitly requires it.

Do not add secrets.

Do not touch unrelated files.

Do not refactor broad areas while implementing a narrow task.

Do not invent models or fields. Read existing models first.

Keep UI Russian where the admin/product UI is Russian.

Add tests for every UI/button/API behavior that can regress.

Run the exact tests listed in the current task before claiming done.

Do not implement future architecture sections until they are marked approved.

Do not rely on Confluence/Jira links as accessible context. They are human references only.

4. Data Pipeline Control Plane v1.2 FINAL — approved implementation scope

Status: approved for implementation.

Goal:

Implement a read-only admin control plane for data quality, enrichment tasks, import batches, queues and recent runs.

Endpoint:

GET /admin/data-pipeline/status

UI page:

/admin/data-pipeline

Hard constraints:

read-only only;

no write actions;

no enqueue/apply/import/recompute;

no BackgroundTask;

no auth/deploy/CI trigger changes;

no migrations or new indexes;

no P0 full-safe-run regression;

no raw technical codes in UI;

manual refresh only; no polling in v1.

Accepted data points:

Overview includes places_without_coordinates.

Recent runs include duration_seconds and error_summary.

Queues always return four canonical queue rows.

UI must render Russian labels, not raw action codes.

Implementation order:

Backend schemas.

Backend status service.

Backend admin endpoint.

Frontend admin page.

Backend tests.

Frontend tests.

Smoke/rollout checklist.

V2, not v1:

cache/last_successful_fetch_at;

city-level breakdown;

automatic polling;

retry/stuck actions;

charts;

drilldown;

new indexes/materialized views;

city bbox coordinate validation;

integration with full-safe-run status.

5. Unified Product Shell v1 — approved architectural base

Core approved rules:

Web, TMA and Bot are presentation-only clients.

Web and TMA use /api/v1/user/*.

No separate /api/v1/tma/* in v1.

Admin API is separate: /api/v1/admin/*.

Bot is gateway / launcher / notifier, not catalog or route UI.

Backend owns product/publication/import/enrichment/quality/route/session state.

Clients send explicit commands and render backend-confirmed state.

No raw technical codes in UI.

No admin fields in user API.

Admin write-actions require dedicated safe endpoints, dry-run, confirmation and audit.

State invariants:

publication_state = published only if quality_state = passed and product_state = active and explicit admin action/approved schedule exists.

quality_state may downgrade automatically, but upgrade to passed requires admin confirmation.

Import/enrichment results do not write directly into product data without approved apply/moderation flow.

Route/session progress is backend-owned.

6. User Web / Site Architecture v1 — approved architectural base

Main flow:

city selection
→ catalog / map / places
→ place detail
→ route build
→ route preview
→ active route flow
→ route editing / continuation

Approved v1 scope:

city selection;

city landing/dashboard;

city readiness display;

catalog list/map;

place detail;

Quick Route;

Category Builder;

Manual Builder;

route preview;

route editing through backend commands/rebuild;

active route basic commands;

shared route read-only;

boot handshake recovery;

mobile-first loading/empty/error/offline states.

V2, not v1:

Advanced Customization Mode;

Slot Builder;

multi-day planning;

complex profile/history/achievements;

reviews;

offline vector maps;

complex offline mutation queue.

Required URL structure:

/city-selection
/[city_slug]
/[city_slug]/catalog
/[city_slug]/map
/[city_slug]/places/[place_id]
/[city_slug]/routes/build
/[city_slug]/routes/preview/[route_id]
/[city_slug]/routes/active
/[city_slug]/shared/[share_token]

Conceptual user API:

GET  /api/v1/user/cities
GET  /api/v1/user/cities/{slug}/readiness
GET  /api/v1/user/places?city_slug=...
GET  /api/v1/user/places/{id}?city_slug=...
POST /api/v1/user/routes/build
GET  /api/v1/user/routes/{id}/preview?city_slug=...
POST /api/v1/user/routes/sessions/commands
GET  /api/v1/user/routes/sessions/active?city_slug=...
GET  /api/v1/user/routes/shared/{share_token}

Hard invariants:

Every city-scoped request must include city_slug.

URL city_slug is primary; body/header cannot silently override it.

Backend validates every city/entity mismatch.

Active route session is bound to city_slug.

Only one active route session per user unless future spec changes it.

localStorage/sessionStorage keys are city-segmented.

Ordinary route must have ≥3 tourist points when enough valid places exist.

Overview route should prefer ≥4 tourist points when enough valid places exist.

Service places must not appear in user catalog, map, route build, route preview or active route.

Service place exclusion is backend-enforced.

Route/session progress is backend-owned.

Offline commands are disabled; no optimistic session mutations in v1.

Shared route is read-only preview and never auto-starts active session.

Web and TMA share /api/v1/user/* response models.

User Web never calls /api/v1/admin/*.

Required future tests:

API contract tests for user endpoints;

city isolation and mismatch rejection;

route minimum points;

service place exclusion;

route build/preview/session command validation;

route recovery after reload/tab switch;

shared route read-only enforcement;

map/list consistency;

raw-code absence in DOM;

mobile viewport behavior;

slow network/offline graceful degradation;

no admin API calls in user web;

no Web/TMA DTO drift.

7. User Web Visual Design v1 — approved design base

Human reference:

https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8257538/CITY+GO+User+Web+Visual+Design+v1

Scope: only User Web / user-facing platform. Admin design and Telegram/TMA design are separate stages.

Approved visual direction:

Premium Urban Explorer

User Web must feel:

mature;

calm;

travel/map-oriented;

modern;

friendly but not childish;

premium enough, not luxury;

practical for walking routes.

Forbidden mood:

childish app;

neon toy interface;

technical dashboard;

admin/debug screen;

random SaaS template;

overloaded map with noisy cards.

Core design principles:

No childish UI.

No random gradients/neon.

No random one-off styling.

Consistent 4px spacing scale.

Clear hierarchy.

One primary CTA per screen.

Readable typography.

Restrained cards.

Map-first where useful.

Strong route timeline.

Russian human-readable UI.

No raw codes.

7.1. Design tokens

Backgrounds and surfaces:

bg-main: #F8F9FA
bg-surface: #FFFFFF
bg-surface-elevated: #FFFFFF
border-neutral: #DCE2E9

Text:

text-primary: #1A1C1E
text-secondary: #43474E
text-muted: #73777F

Route and status:

route-line-future: #B0C4DE
route-line-active: #D96B43
route-step-completed: #8793A1
status-success: #2E7D32
status-warning: #D32F2F

Actions:

action-primary-bg: #1C1E21
action-primary-hover: #2D3135
action-primary-disabled: #E1E2E4
action-secondary-bg: #EDEFEF

Geometry:

radius-sm: 6px
radius-md: 12px
radius-lg: 24px

Shadows:

shadow-sm: 0 2px 4px rgba(0,0,0,0.04)
shadow-lg: 0 8px 24px rgba(0,0,0,0.12)

Spacing scale:

4, 8, 12, 16, 24, 32, 48, 64

Forbidden spacing:

13px, 15px, 17px, random hardcoded spacing

Typography scale:

H1: 28pt / 1.2 / Bold
H2: 20pt / 1.25 / SemiBold
Body large: 13pt / 1.4 / Regular
Body small: 11pt / 1.45 / Regular
Caption: 9pt / 1.3 / Medium

7.2. Layout rules

Desktop:

page max width: 1440px for standard pages;

catalog/route screens use split layout;

content panel: about 400px or 35%;

map panel: about 65%;

list panel scrolls independently from map;

map remains visible on desktop catalog.

Mobile:

map can take full viewport on map/route screens;

content appears in bottom sheet;

bottom sheet states:

peeking: about 72px;

half: about 45vh;

expanded: about 92vh;

primary action remains reachable;

touch targets at least 44px.

7.3. Key component rules

Buttons:

mobile height: 48px;

states: default, hover/active, disabled, loading;

network-action buttons prevent double-submit;

one primary CTA per screen.

Place cards:

white surface;

radius-md;

fixed image aspect ratio;

title max two lines with ellipsis;

no raw metadata;

no stretched images.

Image ratios:

desktop card: 4:3
mobile card: 16:9

Catalog/map:

desktop keeps map visible;

list and map are synchronized;

filters are sticky;

filtering is async, not full reload;

empty results show recovery action;

list must be paginated/virtualized when needed;

map controls do not overlap cards/buttons.

Route design:

route must feel like an interactive guide, not a debug screen;

route preview includes summary, time, distance, places, map, human warnings and start CTA;

active route shows current step, next destination, distance/time, completed/future steps, offline/degraded state;

shared route is read-only and never auto-starts.

7.4. UX states and copy

Loading:

local skeletons;

no global white page;

optional text: “Ищем лучшие места...”

Empty:

В этом районе пока нет мест этой категории. Попробуйте изменить фильтры.

Error:

Не удалось загрузить данные. Проверьте подключение к интернету и попробуйте ещё раз.

Voice:

calm experienced city guide

Rules:

Russian UI;

short verbs;

human-readable labels;

no developer wording;

no raw codes;

no database terms;

no algorithm names;

errors explain recovery action.

7.5. User Web Visual Cursor guardrails

Cursor must not:

use inline styles with random values;

add arbitrary hex colors outside design tokens;

add random gradients or neon colors;

create one-off border radii/shadows/spacing;

use spacing outside 4px scale;

show raw technical codes;

turn route screen into table/debug view;

hide map on desktop catalog;

load all places in large cities at once;

create buttons without disabled/loading states.

Cursor must:

use design tokens;

use the 4px spacing scale;

provide loading/empty/error/offline/degraded states;

lock network-action buttons during request;

keep map/list synchronized;

keep route timeline structure;

keep Russian human-readable copy;

preserve mobile touch target requirements;

add/maintain tests for button states and raw-code absence.

8. Admin Architecture v1 — approved architectural base

Purpose:

Define CITY GO Admin as an operational control plane, not a simple CRUD interface.

Admin roles:

observe → diagnose → review → approve → trigger safe workflows → audit

Admin v1 scope:

operational control plane model;

global vs city-level IA;

read-only vs write boundary;

Data Pipeline read-only relationship;

safe jobs/trigger boundary;

Safe Action pattern;

state ownership and invariants;

publication gating;

emergency hide;

data quality diagnostics;

Route Health diagnostics + safe re-run;

audit log read model;

feature flag safety rules;

UI safety rules;

QA requirements.

Admin URL structure:

/admin/dashboard
/admin/data-pipeline
/admin/audit-log
/admin/taxonomy
/admin/feature-flags
/admin/[city_slug]/overview
/admin/[city_slug]/places
/admin/[city_slug]/places/detail/[id]
/admin/[city_slug]/imports-enrichment
/admin/[city_slug]/publication-staging
/admin/[city_slug]/route-health
/admin/[city_slug]/diagnostics

Hard invariants:

Admin API is separate: /api/v1/admin/*.

User API is separate: /api/v1/user/*.

Admin fields never leak to user API.

Data Pipeline Control Plane is strictly read-only.

No write/repair buttons inside /admin/data-pipeline.

Safe triggers use separate jobs/trigger API.

Every admin write-action requires dry-run/apply/audit, except accelerated emergency hide.

Emergency hide still requires reason, backend validation and audit.

All apply operations require Idempotency-Key.

Browser must not orchestrate multi-step dangerous workflows.

Backend creates audit automatically on every state change.

Publication to published requires quality=passed and product=active.

Quality=passed only through explicit admin confirmation.

Route/session state is read-only for Admin.

Route Health checks are backend-produced, not client-side filters.

Critical route health issues block related publication where applicable.

Admin lists use pagination and URL-persisted filters.

City context is mandatory for city-level admin screens and requests.

Buttons that mutate state must lock disabled/loading after first click.

No raw technical codes in UI.

No auth/deploy/CI/secrets changes in Admin Architecture tasks.

State model:

product state: draft → active → archived
publication state: unpublished → staged → published → hidden
import state: pipeline-owned, admin observes/triggers jobs only
enrichment state: pipeline-owned, admin observes/triggers jobs only
quality state: downgrade can be automatic; passed is manual only
route/session state: admin read-only diagnostics only

Safe Action pattern:

1. Dry-run
2. Affected entities preview
3. Warnings
4. Confirmation
5. Apply with Idempotency-Key
6. Result summary
7. Backend audit log
8. UI refresh

Data Pipeline relationship:

Data Pipeline Control Plane v1.2 FINAL remains strictly read-only.

Admin must not write to Data Pipeline tables from dashboard.

Admin must not repair pipeline output manually.

Admin must not add repair buttons inside /admin/data-pipeline.

Future safe triggers must live outside the read-only dashboard:

POST /api/v1/admin/jobs/trigger
GET  /api/v1/admin/jobs/{job_id}

Emergency hide:

publication_state → hidden
reason required
audit required
no physical delete
accelerated flow allowed

Route Health:

backend-owned diagnostics;

admin displays results;

admin may trigger safe re-run;

admin must not implement route health as client-side filtering.

Admin UX rules:

Russian labels;

no raw codes;

loading/empty/error/degraded states;

disabled/loading buttons for mutations;

double-submit prevention;

URL query persistence for filters/search/page;

city context visible in page header/breadcrumbs;

pagination, not infinite scroll;

refresh affected lists after apply;

mobile-safe emergency/read flows;

structured pages, no “портянка”.

9. Admin Visual Design v1 — approved design base

Human reference:

https://mycitygo.atlassian.net/wiki/spaces/CGO/pages/8290306/CITY+GO+Admin+Visual+Design+v1

Scope: only Admin UI. User Web Visual Design is separate. Telegram/TMA Visual Design is a future stage.

Approved visual direction:

Operational Control Plane

Admin must feel:

mature;

operational;

strict;

calm;

data-dense but readable;

safe-by-default;

Russian human-readable.

Core visual principles:

No “портянка”.

No raw technical codes.

Clear read-only vs write zones.

Clear dangerous actions.

Strong hierarchy.

URL-persistent filters.

Visible city context.

No random colors.

No childish UI.

9.1. Admin design tokens

Interface tones:

bg-admin-main: #F1F3F5
bg-admin-surface: #FFFFFF
bg-admin-sidebar: #1A1D20
border-admin-layout: #CED4DA

Text:

text-admin-primary: #212529
text-admin-secondary: #495057
text-admin-muted: #868E96

Operational actions:

action-safe-bg: #0B7285
action-safe-hover: #0C8599
action-destructive-bg: #C92A2A
action-destructive-hover: #E03131
read-only-indicator: #E9ECEF

Status badges:

status-admin-success-bg: #E6FCF5
status-admin-success-text: #0C8599
status-admin-warning-bg: #FFF9DB
status-admin-warning-text: #F08C00
status-admin-error-bg: #FFE3E3
status-admin-error-text: #C92A2A

Geometry and spacing:

spacing-admin-xs: 4px
spacing-admin-sm: 8px
spacing-admin-md: 16px
spacing-admin-lg: 24px
radius-admin-base: 4px
shadow-admin-flat: 0 1px 2px rgba(0,0,0,0.05)

9.2. Admin layout rules

Desktop shell:

left sidebar: 240px;

top work header: 56px;

content area: remaining space;

shell height: 100vh;

avoid global page scroll where possible;

tables/forms use internal scroll regions;

city context remains visible.

Dashboard grid:

top metric cards;

status/degraded banners;

queue/status panels;

recent run/audit panels;

no uncontrolled vertical data dump.

Detail pages use tabs:

Основная информация
Координаты и карта
Связи с маршрутами
Проверки качества
Журнал аудита

Mobile Admin v1:

only emergency-safe flows;

choose city/object;

see critical status;

emergency hide with reason;

confirm;

see audit result;

complex dashboards/tables are not primary mobile experience.

Emergency touch targets: at least 56x56px.

9.3. Navigation / city context

Global sidebar uses operational sections, not raw DB entities.

Examples:

Мониторинг конвейера данных
Управление городами
Глобальный аудит
Системные задания

City header includes:

current city selector;

city production state indicator;

breadcrumb;

page title;

status summary if relevant.

9.4. Component rules

Buttons:

states: default, hover, focus, disabled, loading;

network-action buttons lock after first click;

safe action buttons use action-safe-bg only for controlled jobs/safe workflows;

destructive buttons require confirmation, reason where applicable and audit result.

Safe Action panel:

Dry-run summary
→ affected entities preview
→ warnings
→ confirmation control
→ apply button locked until confirmation
→ apply loading
→ result summary
→ audit reference

Metric cards show:

metric label;

primary number;

status indicator;

short interpretation;

optional trend/last updated.

Tables:

row height about 40px;

sticky header;

fixed columns where possible;

business identifier first, not UUID;

status badge visible;

updated date formatted;

row actions right-aligned;

long text uses ellipsis + tooltip/detail view;

pagination required;

no infinite scroll.

Filters:

grouped in one filter panel;

URL-persistent;

clear reset action;

loading state after change;

no full page reload.

Status badges:

Russian label;

success/warning/error/neutral mapping;

no snake_case in UI;

not color-only.

9.5. Data Pipeline visual rules

Data Pipeline dashboard is strict read-only.

Allowed:

overall status;

degraded_sections;

quality/backlog metrics;

queue statuses;

recent runs;

last fetched time;

refresh monitoring button.

Forbidden:

edit;

delete;

apply;

retry;

enqueue;

trigger repair;

force import;

mutate queue;

clear queue.

Only allowed action:

Обновить данные мониторинга

Stack traces are never shown inline.

9.6. Safe Action visual flow

Mandatory steps:

Action entry.

Dry-run execution.

Affected entities preview / diff.

Warnings.

Explicit confirmation.

Apply with Idempotency-Key.

Apply loading and UI lock.

Forced refresh of affected data.

Result summary.

Audit reference.

Rules:

browser does not orchestrate dangerous multi-step mutation;

backend owns dry-run/apply/audit;

UI displays backend result;

stale UI must be prevented by refresh.

9.7. Publication / quality / emergency design

Publication UI rules:

publish button hidden or disabled when quality/product state is invalid;

blocked reason visible in Russian;

quality defects shown as actionable checklist/table;

publication confirmation references affected entities;

audit visible after apply.

UI invariant copy:

Публикация доступна только для активных объектов, прошедших проверку качества.

Emergency Hide:

logical hide, not physical delete;

reason required;

confirmation required;

audit result shown;

mobile emergency flow supported.

9.8. Route Health visual rules

Route Health UI is read-only diagnostics + safe re-run trigger.

Backend catches:

routes with too few points;

service places in routes;

city mixing;

long transitions;

poor diversity;

session failures.

Rules:

no client-side route health calculations;

no direct client edits from diagnostics;

safe re-run uses Jobs API;

critical issues block related publication where applicable.

9.9. UX states and copy

Loading:

Загрузка данных из реестра...

Empty:

В выбранном городе не найдено объектов по текущим фильтрам. Измените параметры или сбросьте фильтры.

Error:

Сбой выполнения операции. Повторите попытку через минуту или обратитесь в поддержку.

Degraded:

Часть данных временно недоступна. Отображаются последние доступные сведения.

Stale data:

Данные на экране устарели. Обновите интерфейс перед продолжением.

Voice:

strict operational Russian

Bad → Good examples:

Уничтожить сущность RouteEntity по ID
→ Удалить маршрут и связанные пешеходные треки

status = LOGICAL_DELETE_EMERGENCY
→ Скрыть объект с продакшена

Job triggered successfully. Queue status: OK
→ Автоматическое задание поставлено в очередь обработки.

Validation failed: field description is null
→ Ошибка сохранения: поле «Описание места» обязательно для заполнения.

9.10. Admin Visual Cursor guardrails

Cursor must not:

use inline styles;

add one-off CSS classes detached from tokens;

invent new hex colors;

add random status colors;

show snake_case/raw backend codes;

add write buttons to Data Pipeline dashboard;

mix read-only dashboard and write controls;

create dangerous buttons without confirmation;

create network-action buttons without loading/disabled state;

remove city context from admin header;

implement infinite scroll in admin tables;

compute Route Health client-side;

make mobile admin full analytics in v1.

Cursor must:

use Admin tokens;

use strict admin spacing;

preserve 100vh operational shell where applicable;

keep city context visible;

persist filters/tabs/page in URL;

use pagination;

provide loading/empty/error/degraded/stale states;

lock buttons during requests;

show audit reference after successful write;

keep Data Pipeline read-only;

keep Route Health read-only except safe re-run trigger;

enforce Emergency Hide reason field;

add/maintain tests for raw-code absence, double-submit and URL filter persistence.

9.11. Admin Visual Design QA checklist

Future implementation must pass:

no raw technical text in UI;

no visible id, uuid, object_Object, null, undefined as operator-facing labels;

city context remains visible and URL-persistent;

filter state persists in URL;

write buttons lock after first click;

no double-submit network requests;

pagination appears for lists over threshold;

no infinite scroll in admin tables;

sticky table headers remain visible;

emergency hide blocked until reason is entered;

dangerous action confirmation is clear;

safe action flow shows dry-run/diff/apply/result/audit;

degraded state visible;

stale data state visible;

Data Pipeline dashboard contains no write buttons;

route diagnostics are read-only;

visual regression screenshots reviewed.

9.12. Admin Visual scope

V1 includes:

Admin visual direction;

Admin design tokens;

fixed desktop admin shell;

mobile emergency layout;

navigation/city context rules;

dashboard/metric/table/filter rules;

Safe Action visual flow;

Data Pipeline read-only visual rules;

Publication/quality visual rules;

Emergency Hide visual rules;

Route Health visual rules;

UX states;

copywriting rules;

accessibility rules;

design QA checklist;

Cursor guardrails.

V2:

full-text global search;

visual route graph editor;

role-based UI personalization;

advanced analytics dashboards;

complex bulk repair tools;

full mobile admin beyond emergency flows.

Out:

User Web design;

Telegram/TMA design;

exact component library;

CSS file structure;

React implementation;

implementation task prompt.

10. Telegram Bot / TMA Architecture v1 — approved architectural base

Purpose:

Define how CITY GO uses Telegram as a gateway and mobile route companion without creating a second product, second catalog, or second route logic branch.

Product roles:

Telegram Bot = gateway / launcher / notifier
Telegram Mini App = mobile-first interactive user UI
Backend = auth validation / route engine / session state machine / source of truth
User Web = parallel client using same user API
Admin = separate operational control plane, not accessible from Bot/TMA

Telegram Bot / TMA v1 scope:

Bot as gateway/launcher/notifier;

bot command whitelist;

TMA on /api/v1/user/*;

Telegram initData auth;

replay protection;

deep-link routing;

city/place/route/shared/active route entry points;

backend-owned route/session;

route preview and active route commands;

Web/TMA session continuity;

explicit geolocation/check-in flow;

offline graceful read-only mode;

notification dedup/rate limiting/settings;

admin boundary;

UX safety states;

QA requirements.

Telegram/TMA v2, not v1:

group walks;

audio guides;

complex gamification;

continuous background geotracking, if ever approved;

refresh token complexity, if needed;

offline vector maps;

full profile/history.

Bot allowed commands:

/start
/help
/settings
/my_routes

Bot forbidden behavior:

/search;

/places;

text catalog;

place lists;

inline route builder;

route/session progress storage;

place cache;

admin actions.

TMA v1 screens:

launch/auth splash;

city selection or city dashboard;

catalog/map;

place detail bottom sheet;

route build / quick route;

route preview;

active route wizard;

shared route screen;

notification/settings screen, if needed for subscriptions.

Deep-link payloads:

city_[city_slug]
place_[place_id]
route_[route_id]
share_[share_token]
recover_active

Deep-link rules:

TMA captures start_param before auth or default screen render.

TMA stores it in memory for the current launch.

TMA sends raw initData to backend and waits for auth result.

After successful auth, TMA validates and applies start_param exactly once.

Unknown/expired/invalid payload gracefully falls back to city selection/dashboard.

Shared route opens read-only shared route screen.

Active route recovery uses backend handshake, not local progress.

Telegram auth flow:

TMA receives Telegram initData
→ TMA sends raw initData to backend
→ backend validates HMAC signature
→ backend checks auth_date freshness
→ backend applies replay protection
→ backend maps telegram_id to internal user
→ backend provisions minimal user if absent
→ backend issues short-lived user-scoped token/session

Telegram auth invariants:

client never trusts initDataUnsafe as authenticated identity;

backend validates raw initData HMAC;

backend checks auth_date freshness;

freshness window must be configurable;

replay protection is mandatory;

used initData hash or equivalent replay marker is stored for a short window;

user token has user scope only;

user token cannot access /api/v1/admin/*;

token is short-lived;

no token in localStorage;

expired token triggers re-auth via Telegram initData in v1.

TMA user API only:

POST /api/v1/user/auth/telegram
GET  /api/v1/user/cities
GET  /api/v1/user/cities/{slug}/readiness
GET  /api/v1/user/places?city_slug=...
GET  /api/v1/user/places/{id}?city_slug=...
POST /api/v1/user/routes/build
GET  /api/v1/user/routes/{id}/preview?city_slug=...
GET  /api/v1/user/routes/shared/{share_token}
GET  /api/v1/user/routes/sessions/active?city_slug=...
POST /api/v1/user/routes/sessions/commands

Forbidden APIs:

/api/v1/tma/*
/api/v1/admin/* from TMA or Bot

Route/session invariants:

Route preview is read-only until backend command starts active session.

Preview must not auto-create active session.

Active session starts via backend command.

Backend enforces one active session per user unless future spec changes it.

TMA calls active session handshake on boot/reopen.

TMA does not mutate local progress as source of truth.

Offline commands are disabled.

Web and TMA continue the same backend-owned user session.

Shared route is read-only and does not auto-start active session.

Allowed conceptual route commands:

start
complete_step
skip_step
pause
resume
abandon
finish
update_location, if needed

Geolocation rules:

Source order: Telegram location capability → browser/WebView geolocation fallback → manual start point/manual check-in fallback.

Required states: permission requested, denied, GPS unavailable, stale coordinates, outside selected city, manual fallback.

No continuous geolocation tracking in v1.

No background streaming.

Coordinates are sent only as part of explicit command/check-in/update_location.

Sending is rate-limited.

Backend validates plausibility.

Coordinates are not stored longer than necessary for route/session validation.

User sees clear Russian privacy/permission explanation.

Notification rules:

Sent by backend notification service through Bot API.

Bot only delivers messages.

Dedup/idempotency required.

Rate limiting required.

Unsubscribe/settings required.

Every actionable notification has TMA deep-link.

No admin diagnostics, pipeline failures, import/enrichment internals or generic marketing spam.

No user route/session state stored inside Bot.

Offline rules:

Allowed cache: current/next route step read-only data, recently loaded preview/static place data, UI shell state.

Forbidden cache as authority: route/session progress, completed step index, active status, canonical route order, user identity from initDataUnsafe, long-lived token in localStorage.

Show offline banner.

Show cached read-only step if available.

Disable route/session commands.

No optimistic mutations.

No queued offline commands in v1.

Retry GET requests when network returns.

After reconnect call active session handshake.

Never show white screen as final state.

11. Future design section to add after approval

Telegram/TMA Visual Design v1

Status: not approved yet.

Jira task:

CITYGO-184 — Проработать Telegram Bot / TMA Visual Design v1
Priority: Highest

Will define:

Telegram-native visual behavior;

TMA bottom sheets;

BackButton/MainButton visual patterns;

mobile route companion screens;

Telegram WebView constraints;

bot message visual/copy rules.

12. Future implementation section to add after approval

Implementation Scope

Status: not approved yet.

Cursor must not implement site/admin/TMA architecture until implementation scope is created.

13. Current Cursor Task

Use this section only when explicitly updated before a Cursor session.

Current task: not started from Cursor yet.

Before implementation, read the local workpack content and summarize:

files to touch;

files not to touch;

tests to run;

expected output.

Do not ask for Confluence/Jira access. The local workpack is the available context.