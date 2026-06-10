from pydantic import BaseModel, Field

from schemas.place_seed_item import PlaceSeedItem


class PlaceSeedImportRequest(BaseModel):
    items: list[PlaceSeedItem] = Field(default_factory=list)
    dry_run: bool = True
