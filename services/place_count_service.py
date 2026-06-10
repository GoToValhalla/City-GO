"""
Подсчёт общего числа строк в запросе без влияния limit/offset/order_by.
"""

from sqlalchemy.orm import Query


def get_query_total(query: Query) -> int:
    """
    Возвращает общее количество строк в запросе
    без учета limit / offset / order_by.
    """
    total_query = (
        query.enable_assertions(False)
        .order_by(None)
        .limit(None)
        .offset(None)
    )
    return total_query.count()