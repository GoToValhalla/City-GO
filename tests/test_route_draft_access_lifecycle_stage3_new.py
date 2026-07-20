"""Stage 3: draft ownership, GET read-only view, mutation version order."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from models.route_draft import RouteDraft
from services.route_draft_access import SESSION_HEADER


TOKEN_A = "owner-session-token-aaa"
TOKEN_B = "other-session-token-bbb"


def _headers(token: str = TOKEN_A) -> dict[str, str]:
    return {SESSION_HEADER: token}


def _payload(city_slug: str, token: str = TOKEN_A, **extra):
    body = {
        "city_slug": city_slug,
        "budget_minutes": 120,
        "start": {"type": "city_center"},
        "category_mode": "none",
        "selected_category_slugs": [],
        "seed": 11,
        "session_token": token,
    }
    body.update(extra)
    return body


def _seed_city(city_factory, published_place_factory, slug: str):
    city = city_factory(slug=slug, launch_status="published")
    published_place_factory(slug=f"{slug}-cafe", city_id=city.id, category="cafe")
    published_place_factory(slug=f"{slug}-park", city_id=city.id, category="park")
    published_place_factory(slug=f"{slug}-museum", city_id=city.id, category="museum")
    return city


def test_draft_owner_can_read_and_mutate_new(client, city_factory, published_place_factory):
    city = _seed_city(city_factory, published_place_factory, "draft-owner-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft_id = created["draft_id"]

    read = client.get(f"/routes/drafts/{draft_id}", headers=_headers())
    assert read.status_code == 200
    assert "session_token" not in read.json()
    assert TOKEN_A not in read.text

    removed = client.post(
        f"/routes/drafts/{draft_id}/remove-point",
        headers=_headers(),
        json={"point_id": created["points"][0]["id"], "version": created["version"]},
    )
    assert removed.status_code == 200


def test_draft_missing_wrong_credentials_rejected_new(client, city_factory, published_place_factory):
    city = _seed_city(city_factory, published_place_factory, "draft-cred-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft_id = created["draft_id"]

    assert client.get(f"/routes/drafts/{draft_id}").status_code == 422
    query_leak = client.get(f"/routes/drafts/{draft_id}", params={"session_token": TOKEN_A})
    assert query_leak.status_code == 422

    wrong = client.get(f"/routes/drafts/{draft_id}", headers=_headers(TOKEN_B))
    assert wrong.status_code == 404
    assert wrong.json()["detail"]["code"] == "DRAFT_NOT_FOUND"
    assert TOKEN_B not in wrong.text
    assert "points" not in wrong.json().get("detail", {})

    mutate = client.post(
        f"/routes/drafts/{draft_id}/add-point",
        headers=_headers(TOKEN_B),
        json={"place_id": created["points"][0]["place_id"], "version": created["version"]},
    )
    assert mutate.status_code == 404
    assert TOKEN_B not in mutate.text


def test_draft_cannot_claim_user_id_ownership_new(
    client, db_session, city_factory, published_place_factory
):
    city = _seed_city(city_factory, published_place_factory, "draft-userid-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    draft.user_id = "attacker-user"
    db_session.commit()

    # Ownership remains anonymous session_token; spoofed user_id in body is ignored.
    claimed = client.get(
        f"/routes/drafts/{draft.id}",
        headers=_headers(TOKEN_A),
        params={"user_id": "attacker-user"},
    )
    assert claimed.status_code == 200

    without_token = client.get(
        f"/routes/drafts/{draft.id}",
        params={"user_id": "attacker-user"},
    )
    assert without_token.status_code == 422


def test_draft_expired_and_inactive_rejected_new(client, db_session, city_factory, published_place_factory):
    city = _seed_city(city_factory, published_place_factory, "draft-life-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    draft.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    expired = client.get(f"/routes/drafts/{draft.id}", headers=_headers())
    assert expired.status_code == 404

    draft.expires_at = datetime.utcnow() + timedelta(hours=1)
    draft.status = "closed"
    db_session.commit()
    closed = client.get(f"/routes/drafts/{draft.id}", headers=_headers())
    assert closed.status_code == 404


def test_get_is_idempotent_and_does_not_persist_stale_reconcile_new(
    client, db_session, city_factory, published_place_factory
):
    city = _seed_city(city_factory, published_place_factory, "draft-get-ro-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    target = draft.points[0].place
    stale_id = int(target.id)
    point_count = len(draft.points)
    version = int(draft.version)
    history_len = len(draft.edit_history or [])
    warnings_len = len(draft.warnings or [])

    target.is_published = False
    target.is_visible_in_catalog = False
    target.is_route_eligible = False
    target.publication_status = "draft"
    db_session.commit()

    first = client.get(f"/routes/drafts/{draft.id}", headers=_headers())
    second = client.get(f"/routes/drafts/{draft.id}", headers=_headers())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert stale_id not in {point["place_id"] for point in first.json()["points"]}
    assert any(item["code"] == "STALE_POINTS_OMITTED" for item in first.json()["warnings"])

    db_session.expire_all()
    persisted = db_session.query(RouteDraft).filter(RouteDraft.id == draft.id).one()
    assert int(persisted.version) == version
    assert len(persisted.points) == point_count
    assert stale_id in {int(item.place_id) for item in persisted.points}
    assert len(persisted.edit_history or []) == history_len
    assert len(persisted.warnings or []) == warnings_len
    assert not any(
        item.get("code") == "STALE_POINTS_REMOVED" for item in (persisted.warnings or [])
    )


def test_stale_version_leaves_state_unchanged_even_with_stale_point_new(
    client, db_session, city_factory, published_place_factory
):
    city = _seed_city(city_factory, published_place_factory, "draft-ver-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    target = draft.points[0].place
    target.is_published = False
    target.is_route_eligible = False
    target.is_visible_in_catalog = False
    target.publication_status = "draft"
    db_session.commit()

    before_version = int(draft.version)
    before_points = sorted(int(item.place_id) for item in draft.points)
    before_warnings = list(draft.warnings or [])
    before_history = list(draft.edit_history or [])

    stale = client.post(
        f"/routes/drafts/{created['draft_id']}/remove-point",
        headers=_headers(),
        json={"point_id": created["points"][0]["id"], "version": created["version"] - 1},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_DRAFT_VERSION"

    db_session.expire_all()
    after = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    assert int(after.version) == before_version
    assert sorted(int(item.place_id) for item in after.points) == before_points
    assert list(after.warnings or []) == before_warnings
    assert list(after.edit_history or []) == before_history


def test_stale_point_plus_valid_mutation_one_version_bump_new(
    client, db_session, city_factory, published_place_factory
):
    city = _seed_city(city_factory, published_place_factory, "draft-mut-stale-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    stale_point = draft.points[0]
    keep_point = draft.points[1]
    stale_place = stale_point.place
    stale_place.is_published = False
    stale_place.is_route_eligible = False
    stale_place.is_visible_in_catalog = False
    stale_place.publication_status = "draft"
    db_session.commit()
    version_before = int(draft.version)

    removed = client.post(
        f"/routes/drafts/{draft.id}/remove-point",
        headers=_headers(),
        json={"point_id": keep_point.id, "version": version_before},
    )
    assert removed.status_code == 200
    body = removed.json()
    assert body["version"] == version_before + 1
    assert int(stale_point.place_id) not in {point["place_id"] for point in body["points"]}
    assert int(keep_point.place_id) not in {point["place_id"] for point in body["points"]}

    db_session.expire_all()
    after = db_session.query(RouteDraft).filter(RouteDraft.id == draft.id).one()
    assert int(after.version) == version_before + 1
    assert int(stale_point.place_id) not in {int(item.place_id) for item in after.points}


def test_exception_after_reconcile_rolls_back_new(
    db_session, city_factory, published_place_factory, client
):
    from services.route_draft_loader import get_public_draft_or_error
    from services.route_draft_mutations import remove_point

    city = _seed_city(city_factory, published_place_factory, "draft-rollback-city")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    draft = db_session.query(RouteDraft).filter(RouteDraft.id == created["draft_id"]).one()
    target = draft.points[0].place
    target.is_published = False
    target.is_route_eligible = False
    target.is_visible_in_catalog = False
    target.publication_status = "draft"
    db_session.commit()

    before_version = int(draft.version)
    before_points = sorted(int(item.place_id) for item in draft.points)
    keep_id = int(draft.points[1].id)

    loaded = get_public_draft_or_error(
        db_session, draft.id, session_token=TOKEN_A, for_update=True
    )
    with patch(
        "services.route_draft_mutations.recalculate_draft",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            remove_point(db_session, loaded, keep_id, before_version)

    db_session.expire_all()
    after = db_session.query(RouteDraft).filter(RouteDraft.id == draft.id).one()
    assert int(after.version) == before_version
    assert sorted(int(item.place_id) for item in after.points) == before_points


def test_draft_city_unpublished_hides_draft_new(client, db_session, city_factory, published_place_factory):
    from models.city import City

    city = _seed_city(city_factory, published_place_factory, "draft-city-unpub")
    created = client.post("/routes/random", json=_payload(city.slug)).json()
    db_session.query(City).filter(City.id == city.id).update({"launch_status": "preview"})
    db_session.commit()
    db_session.expire_all()

    hidden = client.get(f"/routes/drafts/{created['draft_id']}", headers=_headers())
    assert hidden.status_code == 404
    assert hidden.json()["detail"]["code"] == "DRAFT_NOT_FOUND"
