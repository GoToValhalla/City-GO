from typing import Literal

from pydantic import BaseModel


class SortingParams(BaseModel):
    """
    Параметры сортировки для list/search endpoint'ов.
    """

    sort_by: Literal["title", "created_at"] = "title"
    sort_order: Literal["asc", "desc"] = "asc"
