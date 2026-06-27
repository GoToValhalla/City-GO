from models.ai_candidate import AICandidate, AITaskRun
from models.review_queue_item import ReviewQueueItem


def _review_item(db_session, place):
    item = ReviewQueueItem(
        city_id=place.city_id,
        place_id=place.id,
        field_name="short_description",
        reason="MISSING_DESCRIPTION",
        severity="medium",
        status="open",
        payload={"current_value": None},
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_ai_selector_lists_choice_first_tasks_and_allowed_providers(client):
    tasks = client.get("/admin/ai/tasks").json()
    explain = next(item for item in tasks if item["key"] == "explain_review_reason")
    parse_hours = next(item for item in tasks if item["key"] == "parse_hours")

    assert explain["enabled"] is True
    assert explain["writes_public_fields"] is False
    assert parse_hours["enabled"] is False

    providers = client.get("/admin/ai/tasks/explain_review_reason/providers").json()
    assert [item["key"] for item in providers] == ["fake_shadow"]


def test_ai_estimate_runs_before_provider_call(client, db_session, place_factory):
    place = place_factory(title="Cafe Meama")
    review_item = _review_item(db_session, place)

    response = client.post(
        "/admin/ai/estimate",
        json={
            "task_type": "explain_review_reason",
            "provider_key": "fake_shadow",
            "review_queue_item_id": review_item.id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estimated_cost_usd"] == 0.0
    assert body["writes_public_fields"] is False
    assert db_session.query(AITaskRun).count() == 0


def test_ai_task_run_requires_explicit_estimate_confirmation(client, db_session, place_factory):
    place = place_factory(title="Cafe Meama")
    review_item = _review_item(db_session, place)

    response = client.post(
        "/admin/ai/task-runs",
        json={
            "task_type": "explain_review_reason",
            "provider_key": "fake_shadow",
            "review_queue_item_id": review_item.id,
            "confirm_estimate": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "confirm_estimate_required"
    assert db_session.query(AITaskRun).count() == 0


def test_ai_task_run_creates_candidate_without_public_place_write(client, db_session, place_factory):
    place = place_factory(title="Cafe Meama")
    review_item = _review_item(db_session, place)

    response = client.post(
        "/admin/ai/task-runs",
        json={
            "task_type": "explain_review_reason",
            "provider_key": "fake_shadow",
            "review_queue_item_id": review_item.id,
            "confirm_estimate": True,
        },
    )

    assert response.status_code == 200
    task_run = response.json()
    assert task_run["status"] == "completed"
    assert task_run["actual_cost_usd"] == 0.0

    candidates = client.get("/admin/ai/candidates").json()
    assert len(candidates) == 1
    assert candidates[0]["candidate_type"] == "explain_review_reason"
    assert candidates[0]["status"] == "pending"

    db_session.refresh(place)
    assert place.short_description is None


def test_ai_candidate_accept_is_audit_state_only(client, db_session, place_factory):
    place = place_factory(title="Cafe Meama")
    review_item = _review_item(db_session, place)
    client.post(
        "/admin/ai/task-runs",
        json={
            "task_type": "explain_review_reason",
            "provider_key": "fake_shadow",
            "review_queue_item_id": review_item.id,
            "confirm_estimate": True,
        },
    )
    candidate = db_session.query(AICandidate).one()

    response = client.post(f"/admin/ai/candidates/{candidate.id}/accept", json={"note": "ok"})

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    db_session.refresh(place)
    assert place.short_description is None
