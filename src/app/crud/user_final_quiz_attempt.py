from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user_final_quiz_attempt import UserFinalQuizAttempt
from ..models.final_quiz import FinalQuiz
from ..models.course import Unit, Course
from ..schemas.user_final_quiz_attempt import (
    UserFinalQuizAttemptCreate, 
    UserFinalQuizAttemptUpdate,
    UserFinalQuizAttemptWithDetails,
    UserFinalQuizAttemptListResponse
)


class UserFinalQuizAttemptCRUD:
    """CRUD operations for UserFinalQuizAttempt model"""
    
    @staticmethod
    async def create_attempt(
        db: AsyncSession, 
        user_id: int, 
        final_quiz_id: int
    ) -> UserFinalQuizAttempt:
        """Create a new final quiz attempt"""
        
        # Check if user already has an incomplete attempt for this quiz
        existing_attempt = await UserFinalQuizAttemptCRUD.get_incomplete_attempt(
            db, user_id, final_quiz_id
        )
        if existing_attempt:
            return existing_attempt
        
        attempt = UserFinalQuizAttempt(
            user_id=user_id,
            final_quiz_id=final_quiz_id,
            started_at=datetime.now()
        )
        
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt
    
    @staticmethod
    async def update_attempt_score(
        db: AsyncSession,
        attempt_id: int,
        score: float,
        exp_earned: int
    ) -> Optional[UserFinalQuizAttempt]:
        """Update attempt with final score and mark as completed"""
        
        attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
        if not attempt:
            return None
        
        attempt.score = score
        attempt.exp_earned = exp_earned
        attempt.completed_at = datetime.now()
        
        await db.commit()
        await db.refresh(attempt)
        return attempt
    
    @staticmethod
    async def get_attempts_by_user(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_completed_only: bool = False
    ) -> List[UserFinalQuizAttempt]:
        """Get all final quiz attempts for a user"""
        
        query = (
            select(UserFinalQuizAttempt)
            .options(
                selectinload(UserFinalQuizAttempt.final_quiz).selectinload(FinalQuiz.unit).selectinload(Unit.course)
            )
            .where(UserFinalQuizAttempt.user_id == user_id)
        )
        
        if include_completed_only:
            query = query.where(UserFinalQuizAttempt.completed_at.isnot(None))
        
        query = query.order_by(desc(UserFinalQuizAttempt.started_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_attempt_by_quiz(
        db: AsyncSession,
        user_id: int,
        final_quiz_id: int
    ) -> Optional[UserFinalQuizAttempt]:
        """Get user's attempt for a specific final quiz"""
        
        query = (
            select(UserFinalQuizAttempt)
            .where(
                and_(
                    UserFinalQuizAttempt.user_id == user_id,
                    UserFinalQuizAttempt.final_quiz_id == final_quiz_id
                )
            )
            .order_by(desc(UserFinalQuizAttempt.started_at))
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_attempt_by_id(
        db: AsyncSession,
        attempt_id: int
    ) -> Optional[UserFinalQuizAttempt]:
        """Get attempt by ID"""
        
        query = select(UserFinalQuizAttempt).where(UserFinalQuizAttempt.id == attempt_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_incomplete_attempt(
        db: AsyncSession,
        user_id: int,
        final_quiz_id: int
    ) -> Optional[UserFinalQuizAttempt]:
        """Get user's incomplete attempt for a specific final quiz"""
        
        query = (
            select(UserFinalQuizAttempt)
            .where(
                and_(
                    UserFinalQuizAttempt.user_id == user_id,
                    UserFinalQuizAttempt.final_quiz_id == final_quiz_id,
                    UserFinalQuizAttempt.completed_at.is_(None)
                )
            )
            .order_by(desc(UserFinalQuizAttempt.started_at))
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_attempt_stats_by_user(
        db: AsyncSession,
        user_id: int
    ) -> dict:
        """Get final quiz attempt statistics for a user"""
        
        # Total attempts
        total_query = select(func.count(UserFinalQuizAttempt.id)).where(
            UserFinalQuizAttempt.user_id == user_id
        )
        total_result = await db.execute(total_query)
        total_attempts = total_result.scalar() or 0
        
        # Completed attempts
        completed_query = select(func.count(UserFinalQuizAttempt.id)).where(
            and_(
                UserFinalQuizAttempt.user_id == user_id,
                UserFinalQuizAttempt.completed_at.isnot(None)
            )
        )
        completed_result = await db.execute(completed_query)
        completed_attempts = completed_result.scalar() or 0
        
        # Average score
        avg_score_query = select(func.avg(UserFinalQuizAttempt.score)).where(
            and_(
                UserFinalQuizAttempt.user_id == user_id,
                UserFinalQuizAttempt.completed_at.isnot(None)
            )
        )
        avg_score_result = await db.execute(avg_score_query)
        average_score = avg_score_result.scalar()
        
        # Total exp earned
        total_exp_query = select(func.sum(UserFinalQuizAttempt.exp_earned)).where(
            UserFinalQuizAttempt.user_id == user_id
        )
        total_exp_result = await db.execute(total_exp_query)
        total_exp_earned = total_exp_result.scalar() or 0
        
        return {
            "total_attempts": total_attempts,
            "completed_attempts": completed_attempts,
            "incomplete_attempts": total_attempts - completed_attempts,
            "average_score": float(average_score) if average_score else None,
            "total_exp_earned": total_exp_earned,
            "completion_rate": (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0
        }
    
    @staticmethod
    async def get_attempts_with_details(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> UserFinalQuizAttemptListResponse:
        """Get attempts with detailed information"""
        
        attempts = await UserFinalQuizAttemptCRUD.get_attempts_by_user(
            db, user_id, skip, limit
        )
        
        # Get statistics
        stats = await UserFinalQuizAttemptCRUD.get_attempt_stats_by_user(db, user_id)
        
        # Format attempts with details
        attempts_with_details = []
        for attempt in attempts:
            attempt_detail = UserFinalQuizAttemptWithDetails(
                id=attempt.id,
                user_id=attempt.user_id,
                final_quiz_id=attempt.final_quiz_id,
                score=attempt.score,
                exp_earned=attempt.exp_earned,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                is_completed=attempt.completed_at is not None,
                final_quiz_title=attempt.final_quiz.title if attempt.final_quiz else None,
                final_quiz_description=attempt.final_quiz.description if attempt.final_quiz else None,
                unit_title=attempt.final_quiz.unit.title if attempt.final_quiz and attempt.final_quiz.unit else None,
                course_title=attempt.final_quiz.unit.course.title if attempt.final_quiz and attempt.final_quiz.unit and attempt.final_quiz.unit.course else None
            )
            attempts_with_details.append(attempt_detail)
        
        return UserFinalQuizAttemptListResponse(
            attempts=attempts_with_details,
            total=stats["total_attempts"],
            user_id=user_id,
            completed_count=stats["completed_attempts"],
            average_score=stats["average_score"]
        )
    
    @staticmethod
    async def delete_attempt(
        db: AsyncSession,
        attempt_id: int
    ) -> bool:
        """Delete a final quiz attempt"""
        
        attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
        if not attempt:
            return False
        
        await db.delete(attempt)
        await db.commit()
        return True
