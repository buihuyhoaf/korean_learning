from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.exercise import Exercise, ExerciseType, ExerciseQuestion, ExerciseQuestionOption
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
        """Get exercises by lesson ID with optional type filter, including questions and options"""
        query = (
            select(Exercise)
            .options(
                selectinload(Exercise.questions).selectinload(ExerciseQuestion.options)
            )
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
        """Get a single exercise by ID with questions and options"""
        query = (
            select(Exercise)
            .options(
                selectinload(Exercise.questions).selectinload(ExerciseQuestion.options)
            )
            .where(Exercise.id == exercise_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_exercise(db: AsyncSession, exercise_data: ExerciseCreate) -> Exercise:
        """Create a new exercise with questions and options"""
        # Create exercise
        exercise = Exercise(
            lesson_id=exercise_data.lesson_id,
            type=exercise_data.type,
            title=exercise_data.title,
            content=exercise_data.content,
            audio_url=exercise_data.audio_url,
            text_to_speak=exercise_data.text_to_speak,
            transcript=exercise_data.transcript,
            prompt=exercise_data.prompt,
            sample_answer=exercise_data.sample_answer,
            order_index=exercise_data.order_index
        )
        
        db.add(exercise)
        await db.flush()  # Get exercise ID
        
        # Create questions and options
        for question_data in exercise_data.questions:
            question = ExerciseQuestion(
                exercise_id=exercise.id,
                question_text=question_data.question_text,
                explanation=question_data.explanation,
                order_index=question_data.order_index
            )
            db.add(question)
            await db.flush()  # Get question ID
            
            # Create options for this question
            for option_data in question_data.options:
                option = ExerciseQuestionOption(
                    question_id=question.id,
                    option_text=option_data.option_text,
                    is_correct=option_data.is_correct,
                    order_index=option_data.order_index
                )
                db.add(option)
        
        await db.commit()
        
        # Reload with relationships
        await db.refresh(exercise, ["questions", "questions.options"])
        return exercise
    
    @staticmethod
    async def update_exercise(
        db: AsyncSession, 
        exercise_id: int, 
        exercise_data: ExerciseUpdate
    ) -> Optional[Exercise]:
        """Update an existing exercise with questions and options"""
        exercise = await ExerciseCRUD.get_exercise_by_id(db, exercise_id)
        if not exercise:
            return None
        
        # Update exercise fields (exclude questions)
        update_data = exercise_data.model_dump(exclude_unset=True, exclude={"questions"})
        for field, value in update_data.items():
            setattr(exercise, field, value)
        
        # Update questions if provided (full replace)
        if "questions" in exercise_data.model_dump(exclude_unset=True):
            # Delete existing questions (cascade will delete options)
            for question in exercise.questions:
                await db.delete(question)
            await db.flush()
            
            # Create new questions
            for question_data in exercise_data.questions:
                question = ExerciseQuestion(
                    exercise_id=exercise.id,
                    question_text=question_data.question_text,
                    explanation=question_data.explanation,
                    order_index=question_data.order_index
                )
                db.add(question)
                await db.flush()
                
                # Create options
                for option_data in question_data.options:
                    option = ExerciseQuestionOption(
                        question_id=question.id,
                        option_text=option_data.option_text,
                        is_correct=option_data.is_correct,
                        order_index=option_data.order_index
                    )
                    db.add(option)
        
        await db.commit()
        
        # Reload with relationships
        await db.refresh(exercise, ["questions", "questions.options"])
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
