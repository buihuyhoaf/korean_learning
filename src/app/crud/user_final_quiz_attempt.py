from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user_final_quiz_attempt import UserFinalQuizAttempt
from ..models.user import User
from ..models.final_quiz import FinalQuiz
from ..models.course import Unit, Course
from ..schemas.user_final_quiz_attempt import (
    UserFinalQuizAttemptCreate, 
    UserFinalQuizAttemptUpdate,
    UserFinalQuizAttemptComplete,
    UserFinalQuizAttemptStatsResponse
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
        
        # Check if user exists
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Check if final quiz exists
        quiz_query = select(FinalQuiz).where(FinalQuiz.id == final_quiz_id)
        quiz_result = await db.execute(quiz_query)
        quiz = quiz_result.scalar_one_or_none()
        if not quiz:
            raise ValueError(f"Final quiz with ID {final_quiz_id} not found")
        
        # Create attempt
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
        """Update attempt with final score and experience"""
        
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
    async def complete_attempt(
        db: AsyncSession,
        attempt_id: int,
        completion_data: UserFinalQuizAttemptComplete
    ) -> Optional[UserFinalQuizAttempt]:
        """Complete a final quiz attempt"""
        
        return await UserFinalQuizAttemptCRUD.update_attempt_score(
            db, attempt_id, completion_data.score, completion_data.exp_earned
        )
    
    @staticmethod
    async def get_attempts_by_user(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_details: bool = True
    ) -> List[UserFinalQuizAttempt]:
        """Get all final quiz attempts for a user"""
        
        query = (
            select(UserFinalQuizAttempt)
            .where(UserFinalQuizAttempt.user_id == user_id)
            .order_by(desc(UserFinalQuizAttempt.started_at))
            .offset(skip)
            .limit(limit)
        )
        
        if include_details:
            query = query.options(
                selectinload(UserFinalQuizAttempt.final_quiz).selectinload(FinalQuiz.unit).selectinload(Unit.course)
            )
        
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
        """Get a specific attempt by ID"""
        
        query = select(UserFinalQuizAttempt).where(UserFinalQuizAttempt.id == attempt_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_attempt_stats(
        db: AsyncSession,
        user_id: int
    ) -> UserFinalQuizAttemptStatsResponse:
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
        
        # Best score
        best_score_query = select(func.max(UserFinalQuizAttempt.score)).where(
            and_(
                UserFinalQuizAttempt.user_id == user_id,
                UserFinalQuizAttempt.completed_at.isnot(None)
            )
        )
        best_score_result = await db.execute(best_score_query)
        best_score = best_score_result.scalar()
        
        # Latest attempt
        latest_query = select(func.max(UserFinalQuizAttempt.started_at)).where(
            UserFinalQuizAttempt.user_id == user_id
        )
        latest_result = await db.execute(latest_query)
        latest_attempt = latest_result.scalar()
        
        return UserFinalQuizAttemptStatsResponse(
            user_id=user_id,
            total_attempts=total_attempts,
            completed_attempts=completed_attempts,
            average_score=average_score,
            total_exp_earned=total_exp_earned,
            best_score=best_score,
            latest_attempt=latest_attempt
        )
    
    @staticmethod
    async def get_active_attempt(
        db: AsyncSession,
        user_id: int,
        final_quiz_id: int
    ) -> Optional[UserFinalQuizAttempt]:
        """Get user's active (incomplete) attempt for a final quiz"""
        
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