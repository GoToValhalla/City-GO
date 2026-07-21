from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.user_signal import RESERVED_SIGNAL_TYPES, UserDerivedProfile, UserSignalCreate, UserSignalRead, UserSignalSummary
from services.anonymous_ownership import optional_anonymous_session, require_anonymous_session
from services.user_signal_service import create_user_signal, derive_user_profile, summarize_user_signals

router = APIRouter(prefix="/user-signals", tags=["user-signals"])

_NOT_FOUND = {"code": "NOT_FOUND", "message": "Resource not found"}


def _is_reserved_signal_type(signal_type: str) -> bool:
    """Case/whitespace-insensitive on purpose: a reserved type must not be
    bypassable by trivial casing or padding tricks (e.g. "Route_Feedback",
    " route_feedback "). Legitimate, non-reserved signal_type values are
    still stored with their original casing -- this check never mutates
    or normalizes the value that gets persisted."""
    return signal_type.strip().lower() in RESERVED_SIGNAL_TYPES


@router.post("/", response_model=UserSignalRead)
def post_user_signal(
    payload: UserSignalCreate,
    anonymous_subject: str | None = Depends(optional_anonymous_session),
    db: Session = Depends(get_db),
) -> UserSignalRead:
    # route_feedback (and any other reserved type) is owned exclusively by
    # the dedicated /route-feedback/ endpoint, which enforces validation
    # and atomic deduplication this generic path does not implement. This
    # endpoint must reject it outright rather than duplicate or proxy that
    # contract -- see schemas/user_signal.py::RESERVED_SIGNAL_TYPES.
    if _is_reserved_signal_type(payload.signal_type):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESERVED_SIGNAL_TYPE",
                "message": "This signal_type is reserved and must be submitted through its dedicated endpoint.",
            },
        )
    subject = anonymous_subject or "anonymous"
    bound = payload.model_copy(update={"user_id": subject})
    return UserSignalRead.model_validate(create_user_signal(db, bound))


@router.get("/summary", response_model=UserSignalSummary)
def get_user_signal_summary(
    subject: str = Depends(require_anonymous_session),
    db: Session = Depends(get_db),
) -> UserSignalSummary:
    return summarize_user_signals(db, subject)


@router.get("/profile", response_model=UserDerivedProfile)
def get_user_derived_profile(
    subject: str = Depends(require_anonymous_session),
    db: Session = Depends(get_db),
) -> UserDerivedProfile:
    return derive_user_profile(db, subject)


@router.get("/{user_id}/summary")
def legacy_user_signal_summary(user_id: str) -> None:
    del user_id
    raise HTTPException(status_code=404, detail=_NOT_FOUND)


@router.get("/{user_id}/profile")
def legacy_user_derived_profile(user_id: str) -> None:
    del user_id
    raise HTTPException(status_code=404, detail=_NOT_FOUND)
