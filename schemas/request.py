from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Location(BaseModel):
    lat: float
    lng: float
    source: Optional[str] = "gps"


class RecommendationRequest(BaseModel):
    """
    Минимальный request для MVP
    (дальше будем расширять под blueprint)
    """

    start_location: Location
    requested_datetime: datetime

    time_budget_minutes: Optional[int] = 120
    interests: Optional[List[str]] = []

    scenario_type: Optional[str] = "surprise_me"
