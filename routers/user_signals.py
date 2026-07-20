from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.user_signal import UserDerivedProfile, UserSignalCreate, UserSignalRead, UserSignalSummary
from services.anonymous_ownership import optional_anonymous_session, require_anonymous_session
from services.user_signal_service import create_user_signal, derive_user_profile, summarize_user_signals

router = APIRouter(prefix="/user-signals", tags=["user-signals"])

_NOT_FOUND = {"code": "NOT_FOUND", "message": "Resource not found"}


@router.post("/", response_model=UserSignalRead)
def post_user_signal(
    payload: UserSignalCreate,
    anonymous_subject: str | None = Depends(optional_anonymous_session),
    db: Session = Depends(get_db),
) -> UserSignalRead:
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
