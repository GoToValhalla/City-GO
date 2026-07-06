from __future__ import annotations


class PlaceCacheInvalidator:
    def invalidate_place(self, place_id: int) -> None:
        return None


def invalidate_place_cache(place_id: int) -> None:
    PlaceCacheInvalidator().invalidate_place(place_id)
