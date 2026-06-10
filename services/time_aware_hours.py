from datetime import datetime, timedelta

from services.itinerary_time_service import resolve_open_windows_for_datetime

_MAX_WAIT_GAP_MINUTES = 20


def legacy_hours_status(time_status: str) -> str:
    return {
        "ok": "open",
        "wait_before_opening": "open",
        "closed_at_arrival": "closed",
        "closes_during_visit": "closes_soon",
        "hours_unknown": "unknown",
    }.get(time_status, "unknown")


def time_status_and_warning(
    opening_hours: object,
    arrival: datetime,
    departure: datetime,
) -> tuple[str, str | None]:
    if opening_hours_unknown(opening_hours):
        return ("hours_unknown", "Часы работы неизвестны — проверьте расписание перед визитом.")
    windows = resolve_open_windows_for_datetime(opening_hours, arrival)
    if not windows:
        return ("hours_unknown", "Не удалось разобрать часы работы на выбранный день.")
    window = find_window_for_arrival(windows, arrival)
    if window is None:
        return ("closed_at_arrival", "Место, вероятно, закрыто к моменту прибытия.")
    return ("ok", None) if departure <= window[1] else (
        "closes_during_visit",
        "Место может закрыться раньше, чем вы закончите визит.",
    )


def apply_wait_gap(
    opening_hours: object,
    arrival: datetime,
    visit_min: int,
) -> tuple[datetime, datetime, str | None]:
    departure = arrival + timedelta(minutes=visit_min)
    if opening_hours_unknown(opening_hours):
        return arrival, departure, None
    windows = resolve_open_windows_for_datetime(opening_hours, arrival)
    next_window = next_window_after_arrival(windows, arrival)
    if next_window is None or find_window_for_arrival(windows, arrival) is not None:
        return arrival, departure, None
    wait_minutes = int((next_window[0] - arrival).total_seconds() // 60)
    if wait_minutes > _MAX_WAIT_GAP_MINUTES:
        return arrival, departure, None
    adjusted_arrival = next_window[0]
    return (
        adjusted_arrival,
        adjusted_arrival + timedelta(minutes=visit_min),
        f"Нужно подождать открытия около {wait_minutes} мин.",
    )


def opening_hours_unknown(opening_hours: object) -> bool:
    return not isinstance(opening_hours, dict) or len(opening_hours) == 0


def find_window_for_arrival(
    windows: list[tuple[datetime, datetime]],
    arrival: datetime,
) -> tuple[datetime, datetime] | None:
    return next(filter(lambda window: window[0] <= arrival <= window[1], windows), None)


def next_window_after_arrival(
    windows: list[tuple[datetime, datetime]],
    arrival: datetime,
) -> tuple[datetime, datetime] | None:
    future = tuple(filter(lambda window: window[0] > arrival, windows))
    return min(future, key=lambda window: window[0]) if future else None
