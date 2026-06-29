from datetime import datetime

from pydantic import BaseModel, ConfigDict

from schemas.external_navigation import ExternalNavigationBlock


# Короткая схема точки внутри маршрута.
# Используется в detail-ответе маршрута.
class RoutePointRead(BaseModel):
    # Идентификатор места.
    place_id: int

    # Порядок точки внутри маршрута.
    position: int

    # Человекочитаемый slug места для перехода на detail-страницу.
    place_slug: str | None = None

    # Заголовок места для отображения в UI.
    place_title: str | None = None

    # Координаты и read-only поля качества нужны frontend-навигации.
    lat: float | None = None
    lng: float | None = None
    category: str | None = None
    address: str | None = None
    is_published: bool | None = None
    is_route_eligible: bool | None = None
    publication_status: str | None = None
    is_active: bool | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Базовая схема маршрута.
# Содержит общие поля, которые нужны и для списка, и для detail.
class RouteBase(BaseModel):
    # Идентификатор города, к которому относится маршрут.
    city_id: int

    # Человекочитаемый slug маршрута для URL.
    slug: str

    # Название маршрута.
    title: str

    # Короткое описание маршрута.
    short_description: str | None = None

    # Примерная длительность маршрута в минутах.
    duration_minutes: int | None = None

    # Примерная дистанция маршрута в километрах.
    distance_km: float | None = None

    # Режим маршрута: walk / public_transport / mixed.
    route_mode: str = "walk"

    # Признак активности маршрута.
    is_active: bool = True


# Схема маршрута для чтения из базы данных.
class RouteRead(RouteBase):
    # Уникальный идентификатор маршрута.
    id: int

    # Дата и время создания записи.
    created_at: datetime

    # Дата и время последнего обновления записи.
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Расширенная схема detail-ответа маршрута.
class RouteDetailRead(RouteRead):
    # Упорядоченный список точек маршрута.
    points: list[RoutePointRead] = []

    # Внешняя навигация — отдельный слой поверх маршрута.
    # Его можно заменить встроенной картой без изменения route engine.
    navigation: ExternalNavigationBlock | None = None
