from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "CityGoBot/0.1 image-enrichment; contact=citygo.local"


def get_json(url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    full_url = f"{url}?{urlencode(params or {})}" if params else url
    request = Request(full_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")
