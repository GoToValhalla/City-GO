"""pipeline_summary_almaty.md из CSV."""

from __future__ import annotations

import csv
from pathlib import Path


def _count_csv(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open(encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)


def _stats_from_places(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    total = with_addr = no_addr = with_photo = no_photo = with_desc = no_desc = 0
    pub = draft = eligible = 0
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            if (row.get("address") or "").strip():
                with_addr += 1
            else:
                no_addr += 1
            if (row.get("image_url") or "").strip():
                with_photo += 1
            else:
                no_photo += 1
            if (row.get("short_description") or "").strip():
                with_desc += 1
            else:
                no_desc += 1
            if row.get("publication_status") == "published":
                pub += 1
            if row.get("publication_status") in {"draft", "needs_review"}:
                draft += 1
            if row.get("is_route_eligible") in {"True", "true", "1"}:
                eligible += 1
    return {
        "total": total, "with_addr": with_addr, "no_addr": no_addr,
        "with_photo": with_photo, "no_photo": no_photo,
        "with_desc": with_desc, "no_desc": no_desc,
        "published": pub, "draft_or_review": draft, "route_eligible": eligible,
    }


def write_summary(root: Path, slug: str, batches: list[str]) -> None:
    places = root / "places_almaty_full.csv"
    s = _stats_from_places(places)
    addr_note = "address_recovery_almaty.csv" if (root / "address_recovery_almaty.csv").exists() else "address_recovery_almaty_NOT_RUN.txt"
    img_note = "image_enrichment_almaty.csv" if (root / "image_enrichment_almaty.csv").exists() else "image_enrichment_almaty_NOT_RUN.txt"
    lines = [
        "# Алматы — сводка pipeline",
        "",
        f"- Текущий slug в БД: **{slug}**",
        f"- Всего мест: **{s.get('total', 0)}**",
        f"- С адресом: {s.get('with_addr', 0)}; без адреса: {s.get('no_addr', 0)}",
        f"- С фото (image_url): {s.get('with_photo', 0)}; без фото: {s.get('no_photo', 0)}",
        f"- С описанием: {s.get('with_desc', 0)}; без описания: {s.get('no_desc', 0)}",
        f"- published: {s.get('published', 0)}; draft/needs_review: {s.get('draft_or_review', 0)}",
        f"- route_eligible: {s.get('route_eligible', 0)}",
        "",
        "## Enrichment batches",
        *([f"- {b}" for b in batches] if batches else ["- нет"]),
        "",
        f"- Address recovery: `{addr_note}`",
        f"- Image enrichment: `{img_note}`",
        "",
        "## Замечание по slug",
        "Канон для API/URL — `almaty` (латиница). Фактический slug: кириллица `алматы`.",
    ]
    (root / "pipeline_summary_almaty.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
