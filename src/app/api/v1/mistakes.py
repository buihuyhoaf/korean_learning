# src/app/api/v1/mistakes.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user import User
from ...models.progress import UserQuestionError
from ...models.question import Question
from ...models.question_type import QuestionType

router = APIRouter(tags=["mistakes"])


# UC7: Review Mistakes
@router.get("/user/{username}/mistakes", response_model=PaginatedListResponse[dict])
async def get_user_mistakes(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    question_type: str = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's mistake history with detailed information"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own mistakes")
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Build query for user question errors
    base_stmt = select(UserQuestionError).where(UserQuestionError.user_id == user.id)
    
    # Filter by question type if specified
    if question_type:
        # NOTE: If QuestionType is a relationship, ensure proper join target is imported/available
        base_stmt = base_stmt.join(Question).join(QuestionType).where(QuestionType.name == question_type)
    
    stmt = base_stmt.order_by(UserQuestionError.error_count.desc(), UserQuestionError.last_wrong_at.desc()).offset(offset).limit(items_per_page)
    mistakes_result = await db.execute(stmt)
    mistakes = mistakes_result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar() or 0
    
    mistakes_data = []
    for mistake in mistakes:
        # Get question details
        question_result = await db.execute(select(Question).where(Question.id == mistake.question_id))
        question = question_result.scalar_one_or_none()
        if not question:
            continue
        
        mistake_dict = {
            "id": mistake.id,
            "question_id": mistake.question_id,
            "question_content": question.content,
            "explanation": question.explanation,
            "last_wrong_answer": mistake.last_wrong_answer,
            "last_wrong_at": mistake.last_wrong_at,
            "error_count": mistake.error_count,
            "lesson_id": question.lesson_id,
            "question_type": {
                "id": question.question_type_relation.id if question.question_type_relation else None,
                "code": question.question_type_relation.code if question.question_type_relation else None,
                "name": question.question_type_relation.name if question.question_type_relation else None,
                "description": question.question_type_relation.description if question.question_type_relation else None
            }
        }
        mistakes_data.append(mistake_dict)
    
    response = paginated_response(
        crud_data={"data": mistakes_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/mistakes/{mistake_id}", response_model=dict)
async def get_mistake_details(
    request: Request,
    username: str,
    mistake_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get detailed information about a specific mistake"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own mistakes")
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    mistake_result = await db.execute(
        select(UserQuestionError).where(
        UserQuestionError.id == mistake_id,
        UserQuestionError.user_id == user.id
        )
    )
    mistake = mistake_result.scalar_one_or_none()
    
    if not mistake:
        raise NotFoundException("Mistake not found")
    
    # Get question details
    question_result = await db.execute(select(Question).where(Question.id == mistake.question_id))
    question = question_result.scalar_one_or_none()
    if not question:
        raise NotFoundException("Question not found")
    
    # Note: UserQuestionAttempt has been removed, so we return empty attempt history
    attempts = []
    
    return {
        "id": mistake.id,
        "question": {
            "id": question.id,
            "content": question.content,
            "media": question.media,
            "explanation": question.explanation,
            "lesson_id": question.lesson_id,
            "question_type": {
                "id": question.question_type_relation.id if question.question_type_relation else None,
                "code": question.question_type_relation.code if question.question_type_relation else None,
                "name": question.question_type_relation.name if question.question_type_relation else None,
                "description": question.question_type_relation.description if question.question_type_relation else None
            },
            "options": [
                {
                    "id": option.id,
                    "option_text": option.option_text,
                    "is_correct": option.is_correct
                }
                for option in question.options
            ]
        },
        "mistake_info": {
            "last_wrong_answer": mistake.last_wrong_answer,
            "last_wrong_at": mistake.last_wrong_at,
            "error_count": mistake.error_count
        },
        "attempt_history": []  # Empty since UserQuestionAttempt is removed
    }


@router.get("/user/{username}/mistakes/summary", response_model=dict)
async def get_mistakes_summary(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get summary of user's mistakes by category and frequency"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own mistakes")
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get all mistakes
    mistakes = db.query(UserQuestionError).filter(UserQuestionError.user_id == user.id).all()
    
    # Group by question type
    mistakes_by_type = {}
    total_mistakes = 0
    most_common_mistakes = []
    
    for mistake in mistakes:
        question = db.query(Question).filter(Question.id == mistake.question_id).first()
        if not question:
            continue
        
        question_type = question.question_type_relation.name if question.question_type_relation else question.question_type
        if question_type not in mistakes_by_type:
            mistakes_by_type[question_type] = {
                "count": 0,
                "total_errors": 0,
                "questions": []
            }
        
        mistakes_by_type[question_type]["count"] += 1
        mistakes_by_type[question_type]["total_errors"] += mistake.error_count
        mistakes_by_type[question_type]["questions"].append({
            "question_id": mistake.question_id,
            "error_count": mistake.error_count,
            "last_wrong_at": mistake.last_wrong_at
        })
        
        total_mistakes += mistake.error_count
        
        # Track most common mistakes
        most_common_mistakes.append({
            "question_id": mistake.question_id,
            "question_content": question.content[:100] + "..." if len(question.content) > 100 else question.content,
            "error_count": mistake.error_count,
            "question_type": question_type
        })
    
    # Sort most common mistakes
    most_common_mistakes.sort(key=lambda x: x["error_count"], reverse=True)
    
    return {
        "total_mistakes": total_mistakes,
        "unique_questions_with_mistakes": len(mistakes),
        "mistakes_by_type": mistakes_by_type,
        "most_common_mistakes": most_common_mistakes[:10],  # Top 10
        "improvement_suggestions": generate_improvement_suggestions(mistakes_by_type)
    }


@router.post("/user/{username}/mistakes/{mistake_id}/practice", response_model=dict)
async def practice_mistake(
    request: Request,
    username: str,
    mistake_id: int,
    practice_answer: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Practice a specific mistake question"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only practice your own mistakes")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    mistake_result = await db.execute(
        select(UserQuestionError).where(
        UserQuestionError.id == mistake_id,
        UserQuestionError.user_id == user.id
        )
    )
    mistake = mistake_result.scalar_one_or_none()
    
    if not mistake:
        raise NotFoundException("Mistake not found")
    
    # Get question details
    question_result = await db.execute(select(Question).where(Question.id == mistake.question_id))
    question = question_result.scalar_one_or_none()
    if not question:
        raise NotFoundException("Question not found")
    
    # Check if answer is correct
    user_answer = practice_answer.get("answer", "")
    is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
    
    # Update mistake record
    if is_correct:
        # If correct, reduce error count (but don't go below 0)
        mistake.error_count = max(0, mistake.error_count - 1)
        mistake.last_wrong_answer = None
        mistake.last_wrong_at = None
    else:
        # If still wrong, update the mistake record
        mistake.last_wrong_answer = user_answer
        mistake.last_wrong_at = datetime.now(UTC)
        mistake.error_count += 1
    
    await db.commit()
    
    return {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "updated_error_count": mistake.error_count,
        "message": "Correct! Great job!" if is_correct else "Not quite right. Keep practicing!"
    }


@router.delete("/user/{username}/mistakes/{mistake_id}", response_model=dict)
async def clear_mistake(
    request: Request,
    username: str,
    mistake_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Clear a mistake record (mark as resolved)"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only clear your own mistakes")
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    mistake_result = await db.execute(
        select(UserQuestionError).where(
        UserQuestionError.id == mistake_id,
        UserQuestionError.user_id == user.id
        )
    )
    mistake = mistake_result.scalar_one_or_none()
    
    if not mistake:
        raise NotFoundException("Mistake not found")
    
    # Clear the mistake record
    db.delete(mistake)
    await db.commit()
    
    return {"message": "Mistake cleared successfully"}


def generate_improvement_suggestions(mistakes_by_type: dict) -> list:
    """Generate improvement suggestions based on mistake patterns"""
    suggestions = []
    
    for question_type, data in mistakes_by_type.items():
        if data["count"] > 5:  # If more than 5 mistakes in this category
            suggestions.append({
                "type": question_type,
                "suggestion": f"Focus more on {question_type} questions. You have {data['count']} questions with mistakes in this category.",
                "priority": "high" if data["count"] > 10 else "medium"
            })
    
    return suggestions


# Admin endpoints for monitoring mistakes
@router.get("/admin/mistakes-stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_mistakes_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get overall mistake statistics (Admin only)"""
    
    # Get total mistakes
    total_mistakes = (await db.execute(select(func.count()).select_from(UserQuestionError))).scalar() or 0
    
    # Get mistakes by question type
    mistakes_by_type = {}
    mistakes_query_result = await db.execute(select(UserQuestionError).join(Question).join(QuestionType))
    mistakes_query = mistakes_query_result.scalars().all()
    
    for mistake in mistakes_query:
        question_result = await db.execute(select(Question).where(Question.id == mistake.question_id))
        question = question_result.scalar_one_or_none()
        if question:
            question_type = question.question_type_relation.name if question.question_type_relation else question.question_type
            if question_type not in mistakes_by_type:
                mistakes_by_type[question_type] = 0
            mistakes_by_type[question_type] += mistake.error_count
    
    # Get most problematic questions
    most_problematic_result = await db.execute(
        select(UserQuestionError).order_by(UserQuestionError.error_count.desc()).limit(10)
    )
    most_problematic = most_problematic_result.scalars().all()
    
    problematic_questions = []
    for mistake in most_problematic:
        question_result = await db.execute(select(Question).where(Question.id == mistake.question_id))
        question = question_result.scalar_one_or_none()
        if question:
            problematic_questions.append({
                "question_id": question.id,
                "question_content": question.content[:100] + "..." if len(question.content) > 100 else question.content,
                "error_count": mistake.error_count,
                "question_type": question.question_type_relation.name if question.question_type_relation else question.question_type
            })
    
    return {
        "total_mistakes": total_mistakes,
        "mistakes_by_type": mistakes_by_type,
        "most_problematic_questions": problematic_questions
    }


