"""Query-cost guards for admin list/search endpoints prone to timeouts on
large tables: /admin/import-queue, /admin/import-jobs, /admin/places (search)."""

from __future__ import annotations

from sqlalchemy import event

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place


def _count_selects(db_session, action, *, table: str | None = None):
    counter = {"n": 0}

    def _before_execute(conn, clauseelement, multiparams, params, execution_options):
        sql = str(clauseelement).lower()
        if "select" not in sql:
            return
        if table is not None and table not in sql:
            return
        counter["n"] += 1

    event.listen(db_session.get_bind(), "before_execute", _before_execute)
    try:
        action()
    finally:
        event.remove(db_session.get_bind(), "before_execute", _before_execute)
    return counter["n"]


def test_admin_import_queue_query_count_does_not_grow_with_job_count_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="lightweight-queue-city")
    for i in range(30):
        db_session.add(CityAdminImportJob(city_id=city.id, status="queued" if i % 2 else "running", source="admin_city_import"))
    db_session.commit()

    query_count = _count_selects(db_session, lambda: client.get("/admin/import-queue"), table="city_admin_import_jobs")

    # Fixed small number of aggregate queries regardless of how many jobs exist —
    # not one query per job (which would explain 502s under production job volume).
    assert query_count <= 5


def test_admin_import_jobs_list_query_count_is_bounded_by_page_size_not_total_jobs_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="lightweight-jobs-city", launch_status="review_required", is_active=False)
    for i in range(40):
        db_session.add(CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import", current_step="ready_for_review"))
    db_session.commit()

    query_count = _count_selects(db_session, lambda: client.get("/admin/import-jobs?limit=50"))

    # One page of cities (1 here) plus a small fixed number of batched aggregate
    # queries — must not scale with the 40 historical job rows for this city.
    assert query_count <= 10


def test_admin_places_search_returns_bounded_page_regardless_of_table_size_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="lightweight-places-city")
    for i in range(120):
        db_session.add(Place(city_id=city.id, slug=f"lightweight-place-{i}", title=f"Кафе {i}", lat=54.7, lng=20.5, category="cafe"))
    db_session.commit()

    response = client.get("/admin/places?city_slug=lightweight-places-city&q=кафе&limit=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 20
    assert len(payload["items"]) == 20
    assert payload["total"] == 120


def test_admin_places_search_query_count_does_not_scale_with_result_size_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="lightweight-places-query-city")
    for i in range(80):
        db_session.add(Place(city_id=city.id, slug=f"lightweight-query-place-{i}", title=f"Музей {i}", lat=54.7, lng=20.5, category="museum"))
    db_session.commit()

    query_count = _count_selects(
        db_session,
        lambda: client.get("/admin/places?city_slug=lightweight-places-query-city&q=музей&limit=20"),
        table="places",
    )

    # One count() + one bounded select + a small number of batched image lookups —
    # must not grow per matched place (no N+1 across the 80 matching rows).
    assert query_count <= 5
