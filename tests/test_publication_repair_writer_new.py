from __future__ import annotations

import pytest

from models.place_publication_transition import PlacePublicationTransition
from scripts.repair_publication_states import apply_plan, build_plan
from tests.allure_support import title


@title("Publication repair dry-run never mutates place state or transition ledger")
def test_publication_repair_dry_run_is_read_only(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="repair-dry-run")
    place.is_visible_in_catalog = False
    place.is_searchable = False
    db_session.commit()

    plan = build_plan(
        db_session,
        city_slug=None,
        restore_cities=False,
        repair_place_flags=True,
        limit=None,
    )

    db_session.refresh(place)
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert db_session.query(PlacePublicationTransition).count() == 0
    assert [item["place_id"] for item in plan["place_changes"]] == [place.id]


@title("Publication repair writes through canonical transition ledger")
def test_publication_repair_apply_records_transition(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="repair-apply")
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    db_session.commit()

    plan = build_plan(
        db_session,
        city_slug=None,
        restore_cities=False,
        repair_place_flags=True,
        limit=None,
    )
    apply_plan(db_session, plan)
    db_session.refresh(place)

    assert place.publication_status == "published"
    assert place.publication_reason_code is None
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True

    transition = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .one()
    )
    assert transition.from_status == "published"
    assert transition.to_status == "published"
    assert transition.reason_code == "published"
    assert transition.actor == "repair_publication_states"
    assert transition.source == "repair_script"
    assert transition.reason_details["repair_kind"] == "published_flag_consistency"


@title("Publication repair owns rollback when canonical writer fails")
def test_publication_repair_rolls_back_all_changes_on_failure(
    db_session,
    published_place_factory,
    monkeypatch,
) -> None:
    first = published_place_factory(slug="repair-rollback-first")
    second = published_place_factory(slug="repair-rollback-second")
    first.is_visible_in_catalog = False
    second.is_visible_in_catalog = False
    db_session.commit()

    plan = build_plan(
        db_session,
        city_slug=None,
        restore_cities=False,
        repair_place_flags=True,
        limit=None,
    )

    from scripts import repair_publication_states as module

    real_transition = module.transition_place_publication
    calls = 0

    def fail_on_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("forced writer failure")
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(module, "transition_place_publication", fail_on_second)

    with pytest.raises(RuntimeError, match="forced writer failure"):
        apply_plan(db_session, plan)

    db_session.refresh(first)
    db_session.refresh(second)
    assert first.is_visible_in_catalog is False
    assert second.is_visible_in_catalog is False
    assert db_session.query(PlacePublicationTransition).count() == 0
