from __future__ import annotations

from models.destination import Destination, DestinationScope


def destination_with_scope(db_session, city_factory, slug: str = "curonian-small") -> tuple[object, Destination, DestinationScope]:
    city = city_factory(slug=f"{slug}-city", center_lat=54.75, center_lng=20.5, launch_status="published", is_active=True)
    dest = Destination(
        slug=slug,
        name="Куршская коса",
        destination_type="tourist_cluster",
        legacy_city_id=city.id,
        center_lat=54.75,
        center_lng=20.5,
        bbox={"south": 54.7, "north": 54.8, "west": 20.4, "east": 20.6},
        is_active=True,
        is_published=True,
    )
    db_session.add(dest)
    db_session.flush()
    scope = DestinationScope(
        destination_id=dest.id,
        code="core",
        name="Основной контур",
        scope_type="catalog",
        import_strategy="single_bbox",
        import_profile="tourist_core",
        is_walkable_cluster=True,
        bbox=dest.bbox,
        enabled=True,
        priority=10,
    )
    db_session.add(scope)
    db_session.commit()
    return city, dest, scope
