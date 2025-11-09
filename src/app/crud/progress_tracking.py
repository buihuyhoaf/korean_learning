"""
Progress Tracking Logic for Course, Unit, Lesson

This module provides functions to automatically calculate and update
progress percentages for lessons, units, and courses based on user activities.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, UTC
import math
from dataclasses import dataclass
from collections import Counter
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.progress import UserLessonProgress, UserUnitProgress, UserCourseProgress
from ..models.question import Question
from ..models.question_option import QuestionOption
from ..models.exercise import Exercise
from ..models.course import Lesson, Unit, Course


@dataclass
class LessonExpBreakdown:
    question_exp: float = 0.0
    listening_exp: float = 0.0
    speaking_exp: float = 0.0
    writing_exp: float = 0.0

    def clamp_non_negative(self) -> "LessonExpBreakdown":
        return LessonExpBreakdown(
            question_exp=max(0.0, self.question_exp),
            listening_exp=max(0.0, self.listening_exp),
            speaking_exp=max(0.0, self.speaking_exp),
            writing_exp=max(0.0, self.writing_exp)
        )


@dataclass
class LessonProgressComputation:
    progress_percent: float
    completed_questions: int
    completed_exercises: int


class ProgressTrackingCRUD:
    """CRUD operations for progress tracking"""
    
    # ============================================================================
    # LESSON PROGRESS CALCULATION
    # ============================================================================
    
    @staticmethod
    async def calculate_lesson_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID
    ) -> LessonProgressComputation:
        """Calculate lesson progress percentage based on:
        - Questions answered correctly (practice questions)
        - Exercises completed
        """
        
        lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            return LessonProgressComputation(0.0, 0, 0)
        
        questions_query = select(Question).filter(Question.lesson_id == lesson_id)
        questions_result = await db.execute(questions_query)
        questions = questions_result.scalars().all()
        total_questions = len(questions)
        
        exercises_query = select(Exercise).filter(Exercise.lesson_id == lesson_id)
        exercises_result = await db.execute(exercises_query)
        exercises = exercises_result.scalars().all()
        total_exercises = len(exercises)
        
        total_items = total_questions + total_exercises
        if total_items == 0:
            return LessonProgressComputation(100.0, total_questions, total_exercises)
        
        progress_check_query = select(UserLessonProgress).filter(
            and_(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.lesson_id == lesson_id
            )
        )
        progress_check_result = await db.execute(progress_check_query)
        existing_progress = progress_check_result.scalar_one_or_none()
        
        if existing_progress:
            completed_questions = max(
                0,
                min(existing_progress.completed_questions_count, total_questions)
            )
            completed_exercises = max(
                0,
                min(existing_progress.completed_exercises_count, total_exercises)
            )
        else:
            completed_questions = 0
            completed_exercises = 0
        
        progress_percent = round(
            min(((completed_questions + completed_exercises) / total_items) * 100.0, 100.0),
            2
        )
        
        return LessonProgressComputation(
            progress_percent=progress_percent,
            completed_questions=completed_questions,
            completed_exercises=completed_exercises
        )
    
    @staticmethod
    async def _calculate_progress_from_exp(
        db: AsyncSession,
        lesson_id: UUID,
        exp_breakdown: LessonExpBreakdown
    ) -> LessonProgressComputation:
        """Calculate lesson progress based on explicit EXP values provided by the client."""
        normalized_exp = exp_breakdown.clamp_non_negative()
        
        lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            return LessonProgressComputation(0.0, 0, 0)
        
        questions_query = select(Question).filter(Question.lesson_id == lesson_id)
        questions_result = await db.execute(questions_query)
        questions = questions_result.scalars().all()
        total_questions = len(questions)
        
        exercises_query = select(Exercise).filter(Exercise.lesson_id == lesson_id)
        exercises_result = await db.execute(exercises_query)
        exercises = exercises_result.scalars().all()
        
        def map_exercise_type(raw: str | None) -> Optional[str]:
            if not raw:
                return None
            lowered = raw.lower()
            if lowered in {"listening", "audio_comprehension"}:
                return "listening"
            if lowered in {"speaking", "pronunciation"}:
                return "speaking"
            if lowered in {"writing", "writing_practice"}:
                return "writing"
            return None
        
        exercise_type_counts = Counter()
        for exercise in exercises:
            raw_type = getattr(exercise, "type", None)
            mapped = map_exercise_type(str(raw_type) if raw_type is not None else None)
            if mapped:
                exercise_type_counts[mapped] += 1
        
        question_required_exp = lesson.max_exp if total_questions > 0 else 0
        question_exp_per = question_required_exp / total_questions if total_questions > 0 else 0
        question_exp_earned = min(normalized_exp.question_exp, question_required_exp)
        
        if question_exp_per > 0:
            completed_questions = min(
                total_questions,
                math.floor(question_exp_earned / question_exp_per + 1e-9)
            )
        elif total_questions == 0:
            completed_questions = 0
        else:
            completed_questions = total_questions
        
        listening_completed = exercise_type_counts.get("listening", 0) if normalized_exp.listening_exp > 0 else 0
        speaking_completed = exercise_type_counts.get("speaking", 0) if normalized_exp.speaking_exp > 0 else 0
        writing_completed = exercise_type_counts.get("writing", 0) if normalized_exp.writing_exp > 0 else 0
        
        completed_exercises = listening_completed + speaking_completed + writing_completed
        total_exercises = sum(exercise_type_counts.values())
        total_items = total_questions + total_exercises
        
        if total_items == 0:
            return LessonProgressComputation(
                progress_percent=100.0,
                completed_questions=completed_questions,
                completed_exercises=completed_exercises
            )
        
        progress_percent = round(
            min(((completed_questions + completed_exercises) / total_items) * 100.0, 100.0),
            2
        )
        
        return LessonProgressComputation(
            progress_percent=progress_percent,
            completed_questions=completed_questions,
            completed_exercises=completed_exercises
        )
    
    @staticmethod
    async def update_lesson_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID,
        exp_breakdown: Optional[LessonExpBreakdown] = None,
        precomputed: Optional[LessonProgressComputation] = None
    ) -> UserLessonProgress:
        """Update or create lesson progress record"""
        
        if exp_breakdown is not None:
            calculation = await ProgressTrackingCRUD._calculate_progress_from_exp(
                db, lesson_id, exp_breakdown
            )
        elif precomputed is not None:
            calculation = precomputed
        else:
            calculation = await ProgressTrackingCRUD.calculate_lesson_progress(
                db, user_id, lesson_id
            )
        
        progress_percent = calculation.progress_percent
        completed_questions = calculation.completed_questions
        completed_exercises = calculation.completed_exercises
        
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
            existing_progress.completed_questions_count = completed_questions
            existing_progress.completed_exercises_count = completed_exercises
            
            if is_completed and existing_progress.completed_at is None:
                existing_progress.completed_at = datetime.now(UTC)
            
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
                completed_at=datetime.now(UTC) if is_completed else None,
                completed_questions_count=completed_questions,
                completed_exercises_count=completed_exercises
            )
            db.add(new_progress)
            
            await db.commit()
            await db.refresh(new_progress)
            return new_progress
    
    # ============================================================================
    # UNIT PROGRESS CALCULATION
    # ============================================================================
    
    @staticmethod
    async def calculate_unit_progress(
        db: AsyncSession,
        user_id: UUID,
        unit_id: UUID
    ) -> float:
        """Calculate unit progress percentage based on lessons completed."""
        
        # Get unit
        unit_query = select(Unit).options(
            selectinload(Unit.lessons)
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
        
        # Progress = average lesson progress
        progress = average_lesson_progress
        
        return round(progress, 2)
    
    @staticmethod
    async def update_unit_progress(
        db: AsyncSession,
        user_id: UUID,
        unit_id: UUID,
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
        user_id: UUID,
        course_id: UUID
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
        user_id: UUID,
        course_id: UUID,
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
        user_id: UUID,
        lesson_id: UUID,
        exp_breakdown: Optional[LessonExpBreakdown] = None
    ) -> dict:
        """Update progress for lesson, unit, and course after lesson activity"""
        
        # Update lesson progress
        lesson_progress = await ProgressTrackingCRUD.update_lesson_progress(
            db, user_id, lesson_id, exp_breakdown=exp_breakdown
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

