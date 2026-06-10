from __future__ import annotations

import re
from urllib.parse import urljoin

from data.scripts.image_pipeline.http_client import fetch_text

OG_RE = re.compile(
    r"<meta[^>]+(?:property|name)=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']",
    re.I,
)


def extract_og_image(html: str, base_url: str) -> str | None:
    match = OG_RE.search(html)
    return urljoin(base_url, match.group(1)) if match else None


def fetch_og_image(website: str) -> dict[str, str] | None:
    image = extract_og_image(fetch_text(website), website)
    if not image:
        return None
    return {"url": image, "source_url": website, "source": "official_website"}
