# CITYGO-171 · Data Quality Gate

The full product and implementation plan is documented in Confluence:

- `CITYGO-171 · P0 Data Quality Gate`
- Parent: `CITY GO Route Builder v2 Production Integration`

Implementation summary:

- Pause new route UI/session/constructor work until data quality gate is fixed.
- Create a single route eligibility policy.
- Route eligibility must use canonical category only.
- Unknown/null eligibility is fail-closed.
- Medical/service/transport/utility/generic OSM places must not be tourist route stops.
- Admin excluded/unknown route metrics must be truthful.
- Route assembly must not return large budget overflows as normal success.
- Production smoke must validate route content.
- Backend and UI automation must pass before the task is considered done.

Definition of done:

- Yerevan 120-minute quick route contains no medical/service/junk/generic OSM places.
- `Институт хирургии им. Микаеляна` never appears in tourist routes.
- `Место для прогулки OSM <id>` is not route eligible.
- Admin `Исключены из маршрутов` is not falsely zero.
- Route does not show `284/120` as normal success.
- UI tests confirm implementation matches the specification.
