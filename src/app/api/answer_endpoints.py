"""
API Endpoints for User Answers

Provides REST API endpoints for retrieving user answer history.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.dependencies import get_current_user
from ..core.db.database import async_get_db
from ..schemas.answer_schemas import AnswerResponse
from ..crud.answer_crud import AnswerCRUD

router = APIRouter(tags=["answers"], prefix="/answers")


@router.get("/question/{question_id}", response_model=Optional[AnswerResponse])
async def get_my_answer_for_question(
    question_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> Optional[AnswerResponse]:
    """
    Get current user's answer for a specific question.
    
    Returns the most recent answer if the user has answered this question before.
    """
    user_id = current_user["id"]
    return await AnswerCRUD.get_user_answer(db, user_id, question_id)


@router.get("/history", response_model=list[AnswerResponse])
async def get_my_answer_history(
    question_id: Optional[int] = Query(None, description="Filter by question ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list[AnswerResponse]:
    """
    Get current user's answer history.
    
    Optionally filter by question_id to get all answers for a specific question.
    Results are ordered by answered_at (most recent first).
    """
    user_id = current_user["id"]
    return await AnswerCRUD.get_user_answer_history(db, user_id, question_id, skip, limit)

