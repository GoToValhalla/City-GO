"""Package 3: collections, collection-places, place-tags public gates."""

from __future__ import annotations

from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place_tag import PlaceTag
from models.tag import Tag


def test_collections_hide_unpublished_city_new(client, db_session, city_factory):
    published = city_factory(slug="p3-col-pub")
    preview = city_factory(slug="p3-col-preview", launch_status="preview")
    db_session.add_all(
        [
            Collection(city_id=published.id, slug="p3-col-ok", title="Ok", is_active=True),
            Collection(city_id=preview.id, slug="p3-col-hide", title="Hide", is_active=True),
        ]
    )
    db_session.commit()

    listed = client.get("/collections/")
    assert listed.status_code == 200
    slugs = {row["slug"] for row in listed.json()}
    assert "p3-col-ok" in slugs
    assert "p3-col-hide" not in slugs
    assert client.get("/collections/by-slug/p3-col-hide").status_code == 404


def test_collection_places_public_place_only_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    city = city_factory(slug="p3-cp-city")
    collection = Collection(city_id=city.id, slug="p3-cp-col", title="Col", is_active=True)
    db_session.add(collection)
    db_session.flush()
    good = published_place_factory(city_id=city.id, slug="p3-cp-good", category="park")
    bad = place_factory(
        city_id=city.id,
        slug="p3-cp-bad",
        category="park",
        is_published=False,
        is_visible_in_catalog=False,
        publication_status="draft",
    )
    db_session.add_all(
        [
            CollectionPlace(collection_id=collection.id, place_id=good.id, position=1),
            CollectionPlace(collection_id=collection.id, place_id=bad.id, position=2),
        ]
    )
    db_session.commit()

    response = client.get("/collection-places/", params={"collection_id": collection.id})
    assert response.status_code == 200
    place_ids = {row["place_id"] for row in response.json()}
    assert place_ids == {good.id}


def test_place_tags_require_public_place_new(
    client, db_session, city_factory, published_place_factory, place_factory
):
    city = city_factory(slug="p3-pt-city")
    tag = Tag(code="p3-tag", name="P3 Tag", is_active=True)
    db_session.add(tag)
    db_session.flush()
    good = published_place_factory(city_id=city.id, slug="p3-pt-good", category="museum")
    bad = place_factory(
        city_id=city.id,
        slug="p3-pt-bad",
        category="museum",
        is_published=False,
        is_visible_in_catalog=False,
        publication_status="draft",
    )
    db_session.add_all(
        [
            PlaceTag(place_id=good.id, tag_id=tag.id),
            PlaceTag(place_id=bad.id, tag_id=tag.id),
        ]
    )
    db_session.commit()

    listed = client.get("/place-tags/")
    assert listed.status_code == 200
    place_ids = {row["place_id"] for row in listed.json()}
    assert good.id in place_ids
    assert bad.id not in place_ids
    assert client.get("/place-tags/", params={"place_id": bad.id}).json() == []
