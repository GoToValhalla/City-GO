"""Slug helpers for discovery."""

from __future__ import annotations

import re

from services.destination_admin_validation import validate_slug


def suggest_slug(value: str) -> str:
    text = value.lower()
    table = (
        ("а", "a"), ("б", "b"), ("в", "v"), ("г", "g"), ("д", "d"), ("е", "e"), ("ё", "e"),
        ("ж", "zh"), ("з", "z"), ("и", "i"), ("й", "y"), ("к", "k"), ("л", "l"), ("м", "m"),
        ("н", "n"), ("о", "o"), ("п", "p"), ("р", "r"), ("с", "s"), ("т", "t"), ("у", "u"),
        ("ф", "f"), ("х", "h"), ("ц", "c"), ("ч", "ch"), ("ш", "sh"), ("щ", "sh"), ("ы", "y"),
        ("э", "e"), ("ю", "yu"), ("я", "ya"),
    )
    for src, dst in table:
        text = text.replace(src, dst)
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return validate_slug(slug or "destination")
