from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.exercise import Exercise, ExerciseType
from ..schemas.exercise import ExerciseCreate, ExerciseUpdate, ExerciseStatsResponse


class ExerciseCRUD:
    """CRUD operations for Exercise model"""
    
    @staticmethod
    async def get_exercises_by_lesson(
        db: AsyncSession, 
        lesson_id: int,
        exercise_type: Optional[ExerciseType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Exercise]:
        """Get exercises by lesson ID with optional type filter"""
        query = (
            select(Exercise)
            .where(Exercise.lesson_id == lesson_id)
            .order_by(Exercise.order_index, Exercise.created_at)
        )
        
        if exercise_type:
            query = query.where(Exercise.type == exercise_type)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_exercise_by_id(db: AsyncSession, exercise_id: int) -> Optional[Exercise]:
        """Get a single exercise by ID"""
        query = select(Exercise).where(Exercise.id == exercise_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_exercise(db: AsyncSession, exercise_data: ExerciseCreate) -> Exercise:
        """Create a new exercise"""
        exercise = Exercise(
            lesson_id=exercise_data.lesson_id,
            type=exercise_data.type,
            title=exercise_data.title,
            content=exercise_data.content,
            audio_url=exercise_data.audio_url,
            transcript=exercise_data.transcript,
            prompt=exercise_data.prompt,
            sample_answer=exercise_data.sample_answer,
            order_index=exercise_data.order_index
        )
        
        db.add(exercise)
        await db.commit()
        await db.refresh(exercise)
        return exercise
    
    @staticmethod
    async def update_exercise(
        db: AsyncSession, 
        exercise_id: int, 
        exercise_data: ExerciseUpdate
    ) -> Optional[Exercise]:
        """Update an existing exercise"""
        exercise = await ExerciseCRUD.get_exercise_by_id(db, exercise_id)
        if not exercise:
            return None
        
        # Update only provided fields
        update_data = exercise_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exercise, field, value)
        
        await db.commit()
        await db.refresh(exercise)
        return exercise
    
    @staticmethod
    async def delete_exercise(db: AsyncSession, exercise_id: int) -> bool:
        """Delete an exercise"""
        exercise = await ExerciseCRUD.get_exercise_by_id(db, exercise_id)
        if not exercise:
            return False
        
        await db.delete(exercise)
        await db.commit()
        return True
    
    @staticmethod
    async def get_exercise_count_by_lesson(
        db: AsyncSession, 
        lesson_id: int
    ) -> int:
        """Get total exercise count for a lesson"""
        query = select(func.count(Exercise.id)).where(Exercise.lesson_id == lesson_id)
        result = await db.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_exercise_stats_by_lesson(
        db: AsyncSession, 
        lesson_id: int
    ) -> ExerciseStatsResponse:
        """Get exercise statistics for a lesson"""
        # Total count
        total_query = select(func.count(Exercise.id)).where(Exercise.lesson_id == lesson_id)
        total_result = await db.execute(total_query)
        total_exercises = total_result.scalar() or 0
        
        # Count by type
        type_counts = {}
        for exercise_type in ExerciseType:
            count_query = select(func.count(Exercise.id)).where(
                and_(Exercise.lesson_id == lesson_id, Exercise.type == exercise_type)
            )
            count_result = await db.execute(count_query)
            type_counts[exercise_type.value] = count_result.scalar() or 0
        
        return ExerciseStatsResponse(
            lesson_id=lesson_id,
            total_exercises=total_exercises,
            listening_count=type_counts.get("listening", 0),
            speaking_count=type_counts.get("speaking", 0),
            writing_count=type_counts.get("writing", 0),
            pronunciation_count=type_counts.get("pronunciation", 0)
        )
    
    @staticmethod
    async def get_exercises_by_type(
        db: AsyncSession, 
        lesson_id: int, 
        exercise_type: ExerciseType
    ) -> List[Exercise]:
        """Get exercises of a specific type for a lesson"""
        return await ExerciseCRUD.get_exercises_by_lesson(db, lesson_id, exercise_type)
    
    @staticmethod
    async def reorder_exercises(
        db: AsyncSession, 
        lesson_id: int, 
        exercise_ids: List[int]
    ) -> bool:
        """Reorder exercises within a lesson"""
        exercises = []
        for i, exercise_id in enumerate(exercise_ids):
            exercise = await ExerciseCRUD.get_exercise_by_id(db, exercise_id)
            if exercise and exercise.lesson_id == lesson_id:
                exercise.order_index = i
                exercises.append(exercise)
        
        if len(exercises) != len(exercise_ids):
            return False
        
        await db.commit()
        return True
