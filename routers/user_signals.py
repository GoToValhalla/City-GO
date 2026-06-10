from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.user_signal import UserDerivedProfile, UserSignalCreate, UserSignalRead, UserSignalSummary
from services.user_signal_service import create_user_signal, derive_user_profile, summarize_user_signals

router = APIRouter(prefix="/user-signals", tags=["user-signals"])


@router.post("/", response_model=UserSignalRead)
def post_user_signal(
    payload: UserSignalCreate,
    db: Session = Depends(get_db),
) -> UserSignalRead:
    return UserSignalRead.model_validate(create_user_signal(db, payload))


@router.get("/{user_id}/summary", response_model=UserSignalSummary)
def get_user_signal_summary(
    user_id: str,
    db: Session = Depends(get_db),
) -> UserSignalSummary:
    return summarize_user_signals(db, user_id)


@router.get("/{user_id}/profile", response_model=UserDerivedProfile)
def get_user_derived_profile(
    user_id: str,
    db: Session = Depends(get_db),
) -> UserDerivedProfile:
    return derive_user_profile(db, user_id)
