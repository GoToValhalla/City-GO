from __future__ import annotations

import httpx

ApiResult = dict[str, object]
Params = dict[str, object]


async def fetch_health(base_url: str) -> ApiResult:
    try:
        data = await _get_json(base_url, "/health", {})
        status = data.get("status") if isinstance(data, dict) else "unknown"

        return {
            "status": status or "unknown",
            "base_url": base_url,
            "ok": True,
        }
    except Exception as exc:
        return _error(base_url, {"status": "error"}, exc)


async def fetch_items(
    base_url: str,
    path: str,
    params: Params,
) -> ApiResult:
    try:
        data = await _get_json(base_url, path, params)

        # Backend может вернуть список напрямую:
        # /open-now/ -> [...]
        if isinstance(data, list):
            return {
                "ok": True,
                "base_url": base_url,
                "items": data,
                "total": len(data),
            }

        # Backend может вернуть пагинированный объект:
        # /places/ -> {"items": [...], "total": 533, "limit": 20, "offset": 0}
        if isinstance(data, dict):
            items = data.get("items")
            total = data.get("total")
            limit = data.get("limit")
            offset = data.get("offset")

            return {
                "ok": True,
                "base_url": base_url,
                "items": items if isinstance(items, list) else [],
                "total": total if isinstance(total, int) else None,
                "limit": limit if isinstance(limit, int) else None,
                "offset": offset if isinstance(offset, int) else None,
                "raw": data,
            }

        return {
            "ok": True,
            "base_url": base_url,
            "items": [],
            "total": 0,
        }

    except Exception as exc:
        return _error(base_url, {"items": []}, exc)


async def post_json(base_url: str, path: str, payload: Params) -> ApiResult:
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(f"{base_url}{path}", json=payload)
            response.raise_for_status()

        return {
            "ok": True,
            "base_url": base_url,
            "data": response.json(),
        }
    except Exception as exc:
        return _error(base_url, {"data": {}}, exc)


async def _get_json(
    base_url: str,
    path: str,
    params: Params,
) -> object:
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        response = await client.get(f"{base_url}{path}", params=params)
        response.raise_for_status()

    return response.json()


def _error(base_url: str, extra: ApiResult, exc: Exception) -> ApiResult:
    return {
        **extra,
        "base_url": base_url,
        "ok": False,
        "error": str(exc),
    }