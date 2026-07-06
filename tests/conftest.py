"""
Pytest конфигурация и fixtures для всех тестов.
"""

import os

# alembic fileConfig сбрасывает handlers pytest caplog
os.environ["ALEMBIC_SKIP_FILE_CONFIG"] = "1"
from typing import Generator

import allure
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.admin_auth import AdminContext, admin_required
from core.config import settings
from db.base import Base
from db.dependencies import get_db
from tests.allure_support import readable_test_title
from tests.test_db_setup import apply_alembic_migrations

# Регистрация всех ORM-таблиц до create_all (FK на import_batches и др.).
import models.admin_audit_log  # noqa: F401
import models.admin_alert  # noqa: F401
import models.admin_operation  # noqa: F401
import models.feature_toggle  # noqa: F401
import models.product_event  # noqa: F401
import models.system_log  # noqa: F401
import models.bot_event  # noqa: F401
import models.bot_session  # noqa: F401
import models.route_build_event  # noqa: F401
import models.route_generation_run  # noqa: F401
import models.route_generation_candidate  # noqa: F401
import models.category  # noqa: F401
import models.city  # noqa: F401
import models.destination  # noqa: F401
import models.city_admin_import_job  # noqa: F401
import models.city_start_point  # noqa: F401
import models.city_import_scope  # noqa: F401
import models.data_quality  # noqa: F401
import models.data_foundation  # noqa: F401
import models.import_batch  # noqa: F401
import models.import_job_step  # noqa: F401
import models.place_scope_link  # noqa: F401
import models.place  # noqa: F401
import models.place_change_review  # noqa: F401
import models.place_field_confidence  # noqa: F401
import models.place_image  # noqa: F401
import models.place_merge_review  # noqa: F401
import models.place_photo_candidate  # noqa: F401
import models.place_publication_decision  # noqa: F401
import models.place_snapshot  # noqa: F401
import models.place_source_presence  # noqa: F401
import models.place_tag  # noqa: F401
import models.route  # noqa: F401
import models.route_place  # noqa: F401
import models.route_draft  # noqa: F401
import models.review_queue_item  # noqa: F401
import models.source_observation  # noqa: F401
import models.tag  # noqa: F401

from main import app


def _allure_title_for_item(item: pytest.Item) -> str:
    function = getattr(item, "obj", None)
    explicit = getattr(function, "__citygo_allure_title__", None)
    if not explicit:
        explicit = getattr(function, "__allure_display_name__", None)
    return str(explicit or readable_test_title(item.name)).strip()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Give every collected test a stable, readable title in JUnit and Allure."""

    for item in items:
        item.user_properties.append(("display_title", _allure_title_for_item(item)))


@pytest.fixture(autouse=True)
def attach_readable_allure_title(request: pytest.FixtureRequest) -> None:
    allure.dynamic.title(_allure_title_for_item(request.node))


@pytest.fixture(scope="session", autouse=True)
def migrate_session_local_database() -> None:
    """SessionLocal (middleware) использует DATABASE_URL — схема только через alembic."""
    if settings.database_url.startswith("sqlite"):
        apply_alembic_migrations(settings.database_url)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """In-memory SQLite для изолированных тестовых фикстур (get_db override)."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(test_db_url: str):
    """Тестовые данные: metadata.create_all на in-memory (отдельно от SessionLocal)."""
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Создает session для каждого теста с rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def override_get_db(db_session: Session):
    """Override FastAPI dependencies: тестовая БД + bypass admin auth."""
    def _override_get_db():
        yield db_session

    def _bypass_admin_auth() -> AdminContext:
        return AdminContext(actor_id="test-admin", actor_role="admin", auth_source="test")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[admin_required] = _bypass_admin_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db):
    """FastAPI TestClient."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def city_factory(db_session: Session):
    """Factory для создания City объектов."""
    from models.city import City

    def create_city(
        slug: str = "zelenogradsk",
        name: str = "Зеленоградск",
        region: str = "Калининградская область",
        country: str = "Россия",
        timezone: str = "Europe/Moscow",
        center_lat: float = 54.9611,
        center_lng: float = 20.4703,
        is_active: bool = True,
        launch_status: str = "published",
    ) -> City:
        city = City(
            slug=slug,
            name=name,
            region=region,
            country=country,
            timezone=timezone,
            center_lat=center_lat,
            center_lng=center_lng,
            is_active=is_active,
            launch_status=launch_status,
        )
        db_session.add(city)
        db_session.commit()
        db_session.refresh(city)
        return city

    return create_city


@pytest.fixture
def category_factory(db_session: Session):
    """Factory для создания Category объектов."""
    from models.category import Category

    def create_category(
        code: str = "cafe",
        name: str = "Кафе",
        is_active: bool = True,
    ) -> Category:
        category = Category(code=code, name=name, is_active=is_active)
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category

    return create_category


@pytest.fixture
def place_factory(db_session: Session, city_factory, category_factory):
    """Factory для создания Place объектов."""
    from models.place import Place
    from models.category import Category

    city = city_factory()
    default_category = category_factory()
    counter = 0

    def _category_by_code(code: str) -> Category:
        existing = db_session.query(Category).filter(Category.code == code).first()
        if existing is not None:
            return existing
        return category_factory(code=code, name=code)

    def create_place(
        slug: str | None = None,
        title: str = "Test Place",
        city_id: int | None = None,
        category: str | None = None,
        category_id: int | None = None,
        lat: float = 54.9611,
        lng: float = 20.4703,
        address: str | None = None,
        image_url: str | None = None,
        price_level: int | None = None,
        dog_friendly: bool = False,
        family_friendly: bool = False,
        indoor: bool = True,
        outdoor: bool = False,
        is_active: bool = True,
        is_published: bool = True,
        is_visible_in_catalog: bool = True,
        is_route_eligible: bool = True,
        is_searchable: bool = True,
        publication_status: str = "published",
    ):
        nonlocal counter
        counter += 1
        if category_id is not None:
            resolved_category_id = category_id
            resolved_category = category
        elif category is not None:
            category_row = _category_by_code(category)
            resolved_category_id = category_row.id
            resolved_category = category_row.code
        else:
            resolved_category_id = default_category.id
            resolved_category = default_category.code

        place = Place(
            slug=slug or f"test-place-{counter}",
            title=title,
            city_id=city_id or city.id,
            category_id=resolved_category_id,
            category=resolved_category,
            lat=lat,
            lng=lng,
            address=address,
            image_url=image_url,
            price_level=price_level,
            dog_friendly=dog_friendly,
            family_friendly=family_friendly,
            indoor=indoor,
            outdoor=outdoor,
            is_active=is_active,
            is_published=is_published,
            is_visible_in_catalog=is_visible_in_catalog,
            is_route_eligible=is_route_eligible,
            is_searchable=is_searchable,
            publication_status=publication_status,
        )
        db_session.add(place)
        db_session.commit()
        db_session.refresh(place)
        return place

    return create_place


@pytest.fixture
def published_place_factory(place_factory):
    def create_published_place(**kwargs):
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_published", True)
        kwargs.setdefault("is_visible_in_catalog", True)
        kwargs.setdefault("is_route_eligible", True)
        kwargs.setdefault("is_searchable", True)
        kwargs.setdefault("publication_status", "published")
        return place_factory(**kwargs)

    return create_published_place


@pytest.fixture
def draft_place_factory(place_factory):
    def create_draft_place(**kwargs):
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_published", False)
        kwargs.setdefault("is_visible_in_catalog", False)
        kwargs.setdefault("is_route_eligible", False)
        kwargs.setdefault("is_searchable", False)
        kwargs.setdefault("publication_status", "draft")
        return place_factory(**kwargs)

    return create_draft_place


@pytest.fixture
def manual_review_place_factory(place_factory):
    def create_manual_review_place(**kwargs):
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_published", False)
        kwargs.setdefault("is_visible_in_catalog", False)
        kwargs.setdefault("is_route_eligible", False)
        kwargs.setdefault("is_searchable", False)
        kwargs.setdefault("publication_status", "needs_review")
        return place_factory(**kwargs)

    return create_manual_review_place


@pytest.fixture
def auto_backlog_place_factory(place_factory):
    def create_auto_backlog_place(**kwargs):
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_published", False)
        kwargs.setdefault("is_visible_in_catalog", False)
        kwargs.setdefault("is_route_eligible", False)
        kwargs.setdefault("is_searchable", False)
        kwargs.setdefault("publication_status", "auto_backlog")
        return place_factory(**kwargs)

    return create_auto_backlog_place


@pytest.fixture
def hidden_place_factory(place_factory):
    def create_hidden_place(**kwargs):
        kwargs.setdefault("is_active", False)
        kwargs.setdefault("is_published", False)
        kwargs.setdefault("is_visible_in_catalog", False)
        kwargs.setdefault("is_route_eligible", False)
        kwargs.setdefault("is_searchable", False)
        kwargs.setdefault("publication_status", "hidden")
        return place_factory(**kwargs)

    return create_hidden_place
