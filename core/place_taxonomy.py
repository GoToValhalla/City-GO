"""
Каноничный словарь таксономии City GO.

Это source of truth для:
- seed-данных
- фильтров
- backend-валидации
- Telegram bot
- AI / recommendation layer
"""

PLACE_CATEGORIES = [
    "coffee",
    "food",
    "walk",
    "museum",
    "attraction",
    "beach",
    "park",
    "bar",
    "hotel",
    "shopping_mall",
    "pharmacy",
    "clinic",
    "hospital",
    "healthcare",
    "bank",
    "atm",
    "transport",
    "bus_stop",
    "parking",
    "police",
    "toilets",
    "shelter",
    "information",
    "service",
]

PLACE_TAGS = [
    "breakfast",
    "dessert",
    "local_food",
    "specialty_coffee",
    "pet_friendly",
    "kid_friendly",
    "romantic",
    "quiet",
    "budget",
    "premium",
    "panoramic",
    "historical",
    "photo_spot",
    "seasonal",
    "open_late",
    "indoor",
    "outdoor",
]

PLACE_SCENARIO_TAGS = [
    "coffee_now",
    "food_now",
    "walk_now",
    "with_dog",
    "with_kids",
    "date_place",
    "solo_time",
    "first_time_in_city",
    "rainy_day",
    "evening_plan",
    "weekend_plan",
]

PLACE_VIBE_TAGS = [
    "cozy",
    "calm",
    "lively",
    "authentic",
    "touristy",
    "local_favorite",
]

PLACE_RESTRICTION_TAGS = [
    "cash_only",
    "reservation_needed",
    "seasonal_only",
    "may_be_closed_offseason",
    "dog_outdoor_only",
]

USER_SIGNALS = [
    "view_place",
    "save_place",
    "like_place",
    "dislike_place",
    "open_route",
    "open_collection",
    "click_call",
    "click_website",
    "click_build_route",
    "use_nearby",
    "use_open_now",
    "use_coffee",
    "use_food",
    "use_walks",
    "use_with_dog",
]
