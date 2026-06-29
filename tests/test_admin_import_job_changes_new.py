from models.city_admin_import_job import CityAdminImportJob
from models.city_admin_import_job_change import CityAdminImportJobChange


def _job(db_session, city_id: int, **kwargs) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="success", current_step="ready_for_review", **kwargs)
    db_session.add(job)
    db_session.flush()
    return job


def _change(job: CityAdminImportJob, change_type: str, **kwargs) -> CityAdminImportJobChange:
    return CityAdminImportJobChange(job_id=job.id, city_id=job.city_id, change_type=change_type, **kwargs)


def test_import_job_change_model_can_store_created_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="changes-model")
    place = place_factory(city_id=city.id, title="New Cafe", category="cafe")
    job = _job(db_session, city.id)
    row = _change(job, "created", place_id=place.id, place_title=place.title, category=place.category, source="osm")

    db_session.add(row)
    db_session.commit()

    saved = db_session.query(CityAdminImportJobChange).filter_by(job_id=job.id).one()
    assert saved.place_id == place.id
    assert saved.change_type == "created"
    assert saved.place_title == "New Cafe"


def test_import_job_changes_summary_counts_rows_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="changes-summary")
    place = place_factory(city_id=city.id, title="Review Park")
    job = _job(db_session, city.id)
    db_session.add_all([
        _change(job, "created", place_id=place.id, place_title="Review Park"),
        _change(job, "needs_review", place_id=place.id, place_title="Review Park"),
        _change(job, "hidden", place_id=place.id, place_title="Review Park"),
    ])
    db_session.commit()

    payload = client.get(f"/admin/import-jobs/{city.id}/changes/summary").json()

    assert payload["job_id"] == job.id
    assert payload["city_slug"] == "changes-summary"
    assert payload["created"] == 1
    assert payload["needs_review"] == 1
    assert payload["hidden"] == 1


def test_import_job_changes_list_filters_by_created_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="changes-filter")
    place = place_factory(city_id=city.id, title="Created Museum", category="museum")
    job = _job(db_session, city.id)
    db_session.add_all([
        _change(job, "created", place_id=place.id, place_title="Created Museum"),
        _change(job, "needs_review", place_id=place.id, place_title="Needs Review"),
    ])
    db_session.commit()

    payload = client.get(f"/admin/import-jobs/{city.id}/changes?change_type=created").json()

    assert payload["total"] == 1
    assert payload["items"][0]["change_type"] == "created"
    assert payload["items"][0]["place_id"] == place.id


def test_rejected_import_change_can_have_no_place_id_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="changes-rejected")
    job = _job(db_session, city.id)
    db_session.add(_change(job, "rejected", place_title="Bad Object", source="osm", reason="missing_coordinates"))
    db_session.commit()

    payload = client.get(f"/admin/import-jobs/{city.id}/changes?change_type=rejected").json()

    assert payload["total"] == 1
    assert payload["items"][0]["place_id"] is None
    assert payload["items"][0]["reason"] == "missing_coordinates"


def test_import_job_changes_summary_falls_back_to_step_details_new(client, db_session, city_factory) -> None:
    city = city_factory(slug="changes-fallback")
    job = _job(db_session, city.id, step_details={"import_diff": {"created": 2, "rejected": 3, "needs_review": 4}})
    db_session.commit()

    payload = client.get(f"/admin/import-jobs/{city.id}/changes/summary").json()

    assert payload["job_id"] == job.id
    assert payload["created"] == 2
    assert payload["rejected"] == 3
    assert payload["needs_review"] == 4
