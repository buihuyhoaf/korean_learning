"""
Progress Tracking Logic for Course, Unit, Lesson

This module provides functions to automatically calculate and update
progress percentages for lessons, units, and courses based on user activities.
"""

from typing import Optional
from datetime import datetime, UTC
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.progress import UserLessonProgress, UserUnitProgress, UserCourseProgress
from ..models.quiz import Question, QuestionOption
from ..models.exercise import Exercise
from ..models.course import Lesson, Unit, Course


class ProgressTrackingCRUD:
    """CRUD operations for progress tracking"""
    
    # ============================================================================
    # LESSON PROGRESS CALCULATION
    # ============================================================================
    
    @staticmethod
    async def calculate_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> float:
        """Calculate lesson progress percentage based on:
        - Questions answered correctly (practice questions)
        - Exercises completed
        """
        
        # Get lesson
        lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()
        
        if not lesson:
            return 0.0
        
        # Get questions for this lesson
        questions_query = select(Question).filter(Question.lesson_id == lesson_id)
        questions_result = await db.execute(questions_query)
        questions = questions_result.scalars().all()
        total_questions = len(questions)
        
        # Get exercises for this lesson
        exercises_query = select(Exercise).filter(Exercise.lesson_id == lesson_id)
        exercises_result = await db.execute(exercises_query)
        exercises = exercises_result.scalars().all()
        total_exercises = len(exercises)
        
        total_items = total_questions + total_exercises
        
        if total_items == 0:
            return 100.0  # No content, consider completed
        
        # Count completed questions using stored counter on progress record
        progress_check_query = select(UserLessonProgress).filter(
            and_(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.lesson_id == lesson_id
            )
        )
        progress_check_result = await db.execute(progress_check_query)
        existing_progress = progress_check_result.scalar_one_or_none()
        
        if existing_progress:
            completed_questions = max(0, min(existing_progress.completed_questions_count, total_questions))
            completed_exercises = max(0, min(existing_progress.completed_exercises_count, total_exercises))
        else:
            completed_questions = 0
        completed_exercises = 0
        
        # Calculate progress
        question_progress = (completed_questions / total_questions * 100) if total_questions > 0 else 0
        exercise_progress = (completed_exercises / total_exercises * 100) if total_exercises > 0 else 0
        
        # Weighted average (questions 70%, exercises 30%)
        progress = (question_progress * 0.7 + exercise_progress * 0.3) if total_items > 0 else 0
        
        return round(progress, 2)
    
    @staticmethod
    async def update_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int,
        progress_percent: Optional[float] = None
    ) -> UserLessonProgress:
        """Update or create lesson progress record"""
        
        # Calculate progress if not provided
        if progress_percent is None:
            progress_percent = await ProgressTrackingCRUD.calculate_lesson_progress(
                db, user_id, lesson_id
            )
        
        # Check if progress record exists
        progress_query = select(UserLessonProgress).filter(
            and_(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.lesson_id == lesson_id
            )
        )
        progress_result = await db.execute(progress_query)
        existing_progress = progress_result.scalar_one_or_none()
        
        # Check if lesson is completed (>= 80%)
        is_completed = progress_percent >= 80.0
        was_completed = existing_progress.is_completed if existing_progress else False
        
        if existing_progress:
            # Update existing progress
            existing_progress.progress_percent = progress_percent
            existing_progress.is_completed = is_completed
            
            if is_completed and existing_progress.completed_at is None:
                existing_progress.completed_at = datetime.now(UTC)
                
                # Log EXP gain when lesson is newly completed
                if not was_completed:
                    from ..models.gamification import UserExpLog
                    from ..models.user import User
                    lesson_exp_reward = 50  # EXP reward for completing a lesson
                    exp_log = UserExpLog(
                        user_id=user_id,
                        source="lesson_completed",
                        amount=lesson_exp_reward
                    )
                    db.add(exp_log)
                    
                    # Update user EXP
                    user_query = select(User).filter(User.id == user_id)
                    user_result = await db.execute(user_query)
                    user = user_result.scalar_one_or_none()
                    if user:
                        user.exp += lesson_exp_reward
            
            await db.commit()
            await db.refresh(existing_progress)
            return existing_progress
        else:
            # Create new progress record
            new_progress = UserLessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                progress_percent=progress_percent,
                is_completed=is_completed,
                completed_at=datetime.now(UTC) if is_completed else None
            )
            db.add(new_progress)
            
            # Log EXP gain when lesson is completed
            if is_completed:
                from ..models.gamification import UserExpLog
                from ..models.user import User
                lesson_exp_reward = 50  # EXP reward for completing a lesson
                exp_log = UserExpLog(
                    user_id=user_id,
                    source="lesson_completed",
                    amount=lesson_exp_reward
                )
                db.add(exp_log)
                
                # Update user EXP
                user_query = select(User).filter(User.id == user_id)
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()
                if user:
                    user.exp += lesson_exp_reward
            
            await db.commit()
            await db.refresh(new_progress)
            return new_progress
    
    # ============================================================================
    # UNIT PROGRESS CALCULATION
    # ============================================================================
    
    @staticmethod
    async def calculate_unit_progress(
        db: AsyncSession,
        user_id: int,
        unit_id: int
    ) -> float:
        """Calculate unit progress percentage based on:
        - Lessons completed
        - Final quiz passed (if applicable)
        """
        
        # Get unit
        unit_query = select(Unit).options(
            selectinload(Unit.lessons),
            selectinload(Unit.final_quiz)
        ).filter(Unit.id == unit_id)
        unit_result = await db.execute(unit_query)
        unit = unit_result.scalar_one_or_none()
        
        if not unit:
            return 0.0
        
        total_lessons = len(unit.lessons)
        
        if total_lessons == 0:
            return 100.0  # No lessons, consider completed
        
        # Get lesson progresses for this unit
        lesson_ids = [lesson.id for lesson in unit.lessons]
        
        if not lesson_ids:
            return 0.0
        
        lessons_progress_query = select(UserLessonProgress).filter(
            and_(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.lesson_id.in_(lesson_ids)
            )
        )
        lessons_progress_result = await db.execute(lessons_progress_query)
        lessons_progress = lessons_progress_result.scalars().all()
        
        # Calculate average lesson progress
        if lessons_progress:
            total_lesson_progress = sum(lp.progress_percent for lp in lessons_progress)
            average_lesson_progress = total_lesson_progress / total_lessons
        else:
            average_lesson_progress = 0.0
        
        # Check if final quiz exists and is completed
        has_final_quiz = unit.final_quiz is not None
        final_quiz_completed = False
        
        if has_final_quiz:
            # TODO: Check if user has passed final quiz
            # For now, we'll skip this check
            pass
        
        # Progress = average lesson progress * 100%
        # If final quiz exists and completed, unit is 100%
        if has_final_quiz and final_quiz_completed:
            progress = 100.0
        else:
            progress = average_lesson_progress
        
        return round(progress, 2)
    
    @staticmethod
    async def update_unit_progress(
        db: AsyncSession,
        user_id: int,
        unit_id: int,
        progress_percent: Optional[float] = None
    ) -> UserUnitProgress:
        """Update or create unit progress record"""
        
        # Calculate progress if not provided
        if progress_percent is None:
            progress_percent = await ProgressTrackingCRUD.calculate_unit_progress(
                db, user_id, unit_id
            )
        
        # Check if progress record exists
        progress_query = select(UserUnitProgress).filter(
            and_(
                UserUnitProgress.user_id == user_id,
                UserUnitProgress.unit_id == unit_id
            )
        )
        progress_result = await db.execute(progress_query)
        existing_progress = progress_result.scalar_one_or_none()
        
        # Check if unit is completed (>= 80%)
        is_completed = progress_percent >= 80.0
        
        if existing_progress:
            # Update existing progress
            existing_progress.progress_percent = progress_percent
            existing_progress.is_completed = is_completed
            
            if is_completed and existing_progress.completed_at is None:
                existing_progress.completed_at = datetime.now(UTC)
            
            await db.commit()
            await db.refresh(existing_progress)
            return existing_progress
        else:
            # Create new progress record
            new_progress = UserUnitProgress(
                user_id=user_id,
                unit_id=unit_id,
                progress_percent=progress_percent,
                is_completed=is_completed
            )
            db.add(new_progress)
            await db.commit()
            await db.refresh(new_progress)
            return new_progress
    
    # ============================================================================
    # COURSE PROGRESS CALCULATION
    # ============================================================================
    
    @staticmethod
    async def calculate_course_progress(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> float:
        """Calculate course progress percentage based on:
        - Units completed
        """
        
        # Get course
        course_query = select(Course).options(
            selectinload(Course.units)
        ).filter(Course.id == course_id)
        course_result = await db.execute(course_query)
        course = course_result.scalar_one_or_none()
        
        if not course:
            return 0.0
        
        total_units = len(course.units)
        
        if total_units == 0:
            return 100.0  # No units, consider completed
        
        # Get unit progresses for this course
        unit_ids = [unit.id for unit in course.units]
        
        if not unit_ids:
            return 0.0
        
        units_progress_query = select(UserUnitProgress).filter(
            and_(
                UserUnitProgress.user_id == user_id,
                UserUnitProgress.unit_id.in_(unit_ids)
            )
        )
        units_progress_result = await db.execute(units_progress_query)
        units_progress = units_progress_result.scalars().all()
        
        # Calculate average unit progress
        if units_progress:
            total_unit_progress = sum(up.progress_percent for up in units_progress)
            average_unit_progress = total_unit_progress / total_units
        else:
            average_unit_progress = 0.0
        
        return round(average_unit_progress, 2)
    
    @staticmethod
    async def update_course_progress(
        db: AsyncSession,
        user_id: int,
        course_id: int,
        progress_percent: Optional[float] = None
    ) -> UserCourseProgress:
        """Update or create course progress record"""
        
        # Calculate progress if not provided
        if progress_percent is None:
            progress_percent = await ProgressTrackingCRUD.calculate_course_progress(
                db, user_id, course_id
            )
        
        # Check if progress record exists
        progress_query = select(UserCourseProgress).filter(
            and_(
                UserCourseProgress.user_id == user_id,
                UserCourseProgress.course_id == course_id
            )
        )
        progress_result = await db.execute(progress_query)
        existing_progress = progress_result.scalar_one_or_none()
        
        # Check if course is completed (>= 80%)
        is_completed = progress_percent >= 80.0
        
        if existing_progress:
            # Update existing progress
            existing_progress.progress_percent = progress_percent
            existing_progress.is_completed = is_completed
            
            if is_completed and existing_progress.completed_at is None:
                existing_progress.completed_at = datetime.now(UTC)
            
            await db.commit()
            await db.refresh(existing_progress)
            return existing_progress
        else:
            # Create new progress record
            new_progress = UserCourseProgress(
                user_id=user_id,
                course_id=course_id,
                progress_percent=progress_percent,
                is_completed=is_completed,
                started_at=datetime.now(UTC)
            )
            db.add(new_progress)
            await db.commit()
            await db.refresh(new_progress)
            return new_progress
    
    # ============================================================================
    # AUTO-UPDATE ALL PROGRESS
    # ============================================================================
    
    @staticmethod
    async def update_all_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> dict:
        """Update progress for lesson, unit, and course after lesson activity"""
        
        # Update lesson progress
        lesson_progress = await ProgressTrackingCRUD.update_lesson_progress(
            db, user_id, lesson_id
        )
        
        # Get lesson to find unit_id
        lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()
        
        if not lesson:
            return {"lesson_progress": lesson_progress}
        
        # Update unit progress
        unit_progress = await ProgressTrackingCRUD.update_unit_progress(
            db, user_id, lesson.unit_id
        )
        
        # Get unit to find course_id
        unit_query = select(Unit).filter(Unit.id == lesson.unit_id)
        unit_result = await db.execute(unit_query)
        unit = unit_result.scalar_one_or_none()
        
        if not unit:
            return {
                "lesson_progress": lesson_progress,
                "unit_progress": unit_progress
            }
        
        # Update course progress
        course_progress = await ProgressTrackingCRUD.update_course_progress(
            db, user_id, unit.course_id
        )
        
        return {
            "lesson_progress": lesson_progress,
            "unit_progress": unit_progress,
            "course_progress": course_progress
        }

