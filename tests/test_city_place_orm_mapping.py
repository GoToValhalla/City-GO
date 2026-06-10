from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag


def test_city_place_relationship_configures_from_foreign_key() -> None:
    configure_mappers()

    city_relationship = inspect(City).relationships["places"]
    place_relationship = inspect(Place).relationships["city"]

    assert city_relationship.mapper.class_ is Place
    assert place_relationship.mapper.class_ is City
    assert Place.city_id.foreign_keys


def test_related_models_imported_for_mapper_registry() -> None:
    assert Category.__tablename__ == "categories"
    assert Collection.__tablename__ == "collections"
    assert CollectionPlace.__tablename__ == "collection_places"
    assert PlaceSchedule.__tablename__ == "place_schedules"
    assert PlaceTag.__tablename__ == "place_tags"
    assert Route.__tablename__ == "routes"
    assert RoutePlace.__tablename__ == "route_places"
    assert Tag.__tablename__ == "tags"
