from pydantic import BaseModel


class PlaceSearchParams(BaseModel):
    """
    Параметры поиска мест.

    Это подготовка под более чистую search-логику:
    позже можно будет использовать и в API, и в сервисах, и в AI-layer.
    """

    city_id: int | None = None
    city_slug: str | None = None
    category_id: int | None = None
    tag_id: int | None = None
    q: str | None = None
