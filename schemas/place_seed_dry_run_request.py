from pydantic import BaseModel, Field

from schemas.place_seed_item import PlaceSeedItem


class PlaceSeedDryRunRequest(BaseModel):
    """
    Стандартный request payload для dry-run seed-проверки мест.

    Это заготовка под более стабильный контракт:
    позже сюда можно добавить metadata, source_batch_id и dry-run options.
    """

    items: list[PlaceSeedItem] = Field(default_factory=list)
