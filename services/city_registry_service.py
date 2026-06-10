from sqlalchemy.orm import Session

from models.city_candidate import CityCandidate
from models.city_import_scope import CityImportScope
from models.country import Country
from models.region import Region
from schemas.city_expansion import CityCandidateCreate, CountryCreate, ImportScopeCreate, RegionCreate


def create_country(db: Session, payload: CountryCreate) -> Country:
    item = Country(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_region(db: Session, payload: RegionCreate) -> Region:
    item = Region(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_city_candidate(db: Session, payload: CityCandidateCreate) -> CityCandidate:
    item = CityCandidate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_import_scope(db: Session, payload: ImportScopeCreate) -> CityImportScope:
    item = CityImportScope(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_countries(db: Session) -> list[Country]:
    return db.query(Country).order_by(Country.name.asc()).all()


def list_regions(db: Session) -> list[Region]:
    return db.query(Region).order_by(Region.name.asc()).all()


def list_city_candidates(db: Session) -> list[CityCandidate]:
    return db.query(CityCandidate).order_by(CityCandidate.name.asc()).all()


def list_import_scopes(db: Session, city_id: int | None = None) -> list[CityImportScope]:
    query = db.query(CityImportScope)
    if city_id is not None:
        query = query.filter(CityImportScope.city_id == city_id)
    return query.order_by(CityImportScope.priority.asc(), CityImportScope.code.asc()).all()
