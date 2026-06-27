"""Admin AI actions: one-click tasks with minimal settings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_ai import AdminAIRunRequest, AdminAIRunResult, AdminAITasksResponse
from services.admin_ai_service import list_admin_ai_tasks, run_admin_ai_task
from services.openai_client import OpenAIClientError

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.get("/tasks", response_model=AdminAITasksResponse)
def get_admin_ai_tasks(auth: AdminContext = Depends(admin_required)) -> AdminAITasksResponse:
    return list_admin_ai_tasks()


@router.post("/run", response_model=AdminAIRunResult)
def run_admin_ai(
    payload: AdminAIRunRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminAIRunResult:
    try:
        return run_admin_ai_task(db, payload, actor=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpenAIClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
