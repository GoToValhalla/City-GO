import models.taxonomy  # noqa: F401

from models.category import Category
from models.taxonomy import TaxonomyMapping
from services.quality_score_v2 import calculate_quality_v2, publication_ready
from services.route_policy_service import evaluate_category_policy
from services.taxonomy_rule_engine import classify_place


def category(db, code, name, policy="manual_review"):
    row = Category(code=code, name=name, route_policy=policy, route_contexts=[])
    db.add(row); db.commit(); db.refresh(row); return row


def test_exact_mapping_and_manual_override_new(db_session):
    pharmacy = category(db_session, "pharmacy", "Аптека", "useful_only")
    museum = category(db_session, "museum", "Музей", "always_allowed")
    db_session.add(TaxonomyMapping(source="osm", source_key="amenity", source_value="pharmacy", target_category_id=pharmacy.id,
        priority=100, confidence=0.98, active=True, conditions={}, conditions_hash="-", fallback=False, created_by="test"))
    db_session.commit()
    exact = classify_place(db_session, source="osm", source_tags={"amenity":"pharmacy"}, title="Аптека", description=None, current_category="service")
    manual = classify_place(db_session, source="osm", source_tags={"amenity":"pharmacy"}, title="Аптека", description=None, current_category="service", manual_category_id=museum.id)
    assert exact.category_code == "pharmacy" and exact.decision == "auto_apply"
    assert manual.category_code == "museum" and manual.confidence == 1


def test_ambiguous_mapping_requires_review_new(db_session):
    first = category(db_session, "coffee", "Кофейня", "allowed_by_context")
    second = category(db_session, "food", "Кафе", "allowed_by_context")
    for target in (first, second):
        db_session.add(TaxonomyMapping(source="osm", source_key="amenity", source_value="cafe", target_category_id=target.id,
            priority=100, confidence=0.9, active=True, conditions={}, conditions_hash=str(target.id), fallback=False, created_by="test"))
    db_session.commit()
    result = classify_place(db_session, source="osm", source_tags={"amenity":"cafe"}, title="Кафе", description=None, current_category=None)
    assert result.decision == "review"
    assert result.warnings


def test_infrastructure_route_policy_new(db_session):
    pharmacy = category(db_session, "pharmacy", "Аптека", "useful_only")
    assert evaluate_category_policy(pharmacy, context="tourist_walk").allowed is False
    assert evaluate_category_policy(pharmacy, context="practical").allowed is True


def test_category_crud_and_tree_cycle_guard_new(client):
    created = client.post("/admin/taxonomy/categories", json={"code":"custom_gallery","name":"Авторская галерея","route_policy":"always_allowed"})
    assert created.status_code == 201
    parent = client.post("/admin/taxonomy/categories", json={"code":"culture_root","name":"Культура"}).json()
    child = created.json()
    assert client.put("/admin/taxonomy/tree", json={"nodes":[{"id":parent["id"],"parent_id":child["id"]},{"id":child["id"],"parent_id":parent["id"]}]}).status_code == 409


def test_bulk_preview_apply_and_rollback_are_idempotent_new(client, place_factory, category_factory):
    old = category_factory(code="service", name="Услуги")
    target = category_factory(code="pharmacy", name="Аптека")
    place = place_factory(category_id=old.id, category="service")
    body = {"filters":{"category_id":old.id},"target_category_id":target.id,"use_rule_engine":False,
        "update_route_eligibility":False,"idempotency_key":"bulk-test-1","limit":100}
    preview = client.post("/admin/taxonomy/bulk/preview", json=body).json()
    assert preview["preview"]["count"] == 1
    first = client.post("/admin/taxonomy/bulk/apply", json={"batch_id":preview["id"]})
    second = client.post("/admin/taxonomy/bulk/apply", json={"batch_id":preview["id"]})
    assert first.status_code == second.status_code == 200
    assert client.post(f"/admin/taxonomy/bulk/{preview['id']}/rollback").status_code == 200
    assert client.post(f"/admin/taxonomy/bulk/{preview['id']}/rollback").status_code == 200
    assert place.id


def test_quality_v2_has_separate_blockers_new(place_factory):
    place = place_factory(lat=0, lng=0, category_id=None, category=None)
    result = calculate_quality_v2(place)
    assert result.score <= 100
    assert publication_ready(result) is False
    assert result.blocking_issues


def test_workflow_is_idempotent_new(client, place_factory):
    place = place_factory()
    body = {"entity_type":"place","entity_id":str(place.id),"payload":{},"request_id":"req-1","idempotency_key":"same"}
    first = client.post("/admin/workflows/after_category_change/run", json=body)
    second = client.post("/admin/workflows/after_category_change/run", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
