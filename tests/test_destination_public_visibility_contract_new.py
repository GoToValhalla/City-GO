"""Package 3: destination public visibility fail-closed contract."""

from __future__ import annotations

from models.destination import Destination, DestinationPlaceMembership, DestinationScope


def _dest(db, *, slug: str, is_published: bool = True, **kwargs) -> Destination:
    row = Destination(
        slug=slug,
        name=slug,
        destination_type="city",
        is_active=True,
        is_published=is_published,
        center_lat=54.96,
        center_lng=20.47,
        **kwargs,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_unpublished_destination_detail_404_new(client, db_session):
    published = _dest(db_session, slug="p3-dest-pub")
    draft = _dest(db_session, slug="p3-dest-draft", is_published=False)

    assert client.get(f"/v1/destinations/{published.slug}").status_code == 200
    assert client.get(f"/v1/destinations/{draft.slug}").status_code == 404


def test_destination_children_scopes_hide_unpublished_new(client, db_session):
    parent = _dest(db_session, slug="p3-dest-parent")
    visible = _dest(db_session, slug="p3-dest-child-ok")
    hidden = _dest(db_session, slug="p3-dest-child-hide", is_published=False)
    visible.parent_id = parent.id
    hidden.parent_id = parent.id
    db_session.add(
        DestinationScope(
            destination_id=parent.id,
            code="core",
            name="core",
            scope_type="bbox",
            priority=1,
            enabled=True,
        )
    )
    db_session.commit()

    detail = client.get(f"/v1/destinations/{parent.slug}")
    assert detail.status_code == 200
    body = detail.json()
    child_slugs = {row["slug"] for row in body["sub_destinations"]}
    assert visible.slug in child_slugs
    assert hidden.slug not in child_slugs
    assert body["has_children"] is True
    assert len(body["scopes"]) == 1


def test_destination_places_count_public_only_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    city = city_factory(slug="p3-dest-count-city")
    dest = _dest(db_session, slug="p3-dest-count")
    good = published_place_factory(city_id=city.id, slug="p3-dest-good", category="cafe")
    bad = place_factory(
        city_id=city.id,
        slug="p3-dest-bad",
        category="cafe",
        is_published=False,
        is_visible_in_catalog=False,
        publication_status="draft",
    )
    for place in (good, bad):
        db_session.add(
            DestinationPlaceMembership(
                destination_id=dest.id,
                place_id=place.id,
                assignment_type="legacy_city",
                is_primary=True,
            )
        )
    db_session.commit()

    detail = client.get(f"/v1/destinations/{dest.slug}")
    assert detail.status_code == 200
    assert detail.json()["places_count"] == 1
