from pydantic import BaseModel, Field

from schemas.place_seed_item import PlaceSeedItem


class PlaceSeedValidationRequest(BaseModel):
    """
    Стандартный request payload для bulk-валидации seed-элементов мест.

    Это заготовка под более стабильный контракт:
    позже сюда можно добавить metadata, source_batch_id и validation options.
    """

    items: list[PlaceSeedItem] = Field(default_factory=list)
