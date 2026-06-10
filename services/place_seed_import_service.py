from dataclasses import dataclass
from functools import reduce

from sqlalchemy.orm import Session

from schemas.place_seed_import_summary import PlaceSeedImportSummary
from schemas.place_seed_item import PlaceSeedItem
from services.place_seed_dedup_service import deduplicate_place_seed_items
from services.place_seed_import_summary_service import build_place_seed_import_summary
from services.place_seed_normalization_service import normalize_place_seed_item
from services.place_seed_validation_service import validate_place_seed_item
from services.place_seed_write_service import plan_place_seed_write, write_place_seed_item
from services.place_import_log_service import record_place_import

_AUTO_PUBLISH = "auto_publish"
_NEEDS_REVIEW = "needs_review"
_HIDDEN = "hidden"


@dataclass(frozen=True)
class _State:
    created: int = 0
    updated: int = 0
    invalid: int = 0
    errors: tuple[str, ...] = ()
    auto_published: int = 0
    needs_review: int = 0
    rejected: int = 0


def import_place_seed_items(
    db: Session,
    items: list[PlaceSeedItem],
    dry_run: bool = True,
) -> PlaceSeedImportSummary:
    normalized = list(map(normalize_place_seed_item, items))
    dedup = deduplicate_place_seed_items(normalized)
    dup_errors = tuple(map(lambda slug: f"duplicate slug: {slug}", dedup.duplicate_slugs))
    state = reduce(
        lambda acc, item: _apply_item(db, acc, item, dry_run),
        dedup.unique_items,
        _State(errors=dup_errors),
    )
    if not dry_run:
        db.commit()
    summary = build_place_seed_import_summary(
        total=len(items),
        created=state.created,
        updated=state.updated,
        skipped=len(dedup.duplicate_slugs),
        invalid=state.invalid,
        errors=list(state.errors),
        auto_published=state.auto_published,
        needs_review_count=state.needs_review,
        rejected_count=state.rejected,
    )
    record_place_import(db, normalized, summary, dry_run=dry_run, source="place_seed_import")
    return summary


def _apply_item(
    db: Session,
    state: _State,
    item: PlaceSeedItem,
    dry_run: bool,
) -> _State:
    validation = validate_place_seed_item(item)
    if not validation.is_valid:
        return _invalid(state, f"{item.slug} is invalid")
    action = plan_place_seed_write(db, item) if dry_run else write_place_seed_item(db, item)
    if action == "invalid":
        return _invalid(state, f"{item.slug} has unknown city_slug")
    return _increment(state, action)


def _invalid(state: _State, error: str) -> _State:
    return _State(
        state.created, state.updated, state.invalid + 1,
        (*state.errors, error), state.auto_published, state.needs_review, state.rejected,
    )


def _increment(state: _State, action: str) -> _State:
    is_new = action in (_AUTO_PUBLISH, _NEEDS_REVIEW, _HIDDEN, "created")
    return _State(
        created=state.created + (1 if is_new else 0),
        updated=state.updated + (1 if action == "updated" else 0),
        invalid=state.invalid,
        errors=state.errors,
        auto_published=state.auto_published + (1 if action == _AUTO_PUBLISH else 0),
        needs_review=state.needs_review + (1 if action == _NEEDS_REVIEW else 0),
        rejected=state.rejected + (1 if action == _HIDDEN else 0),
    )
