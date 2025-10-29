# CRUD Logic for Questions with Backward Compatibility
# This snippet shows how to handle both quiz_id and lesson_id

from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.question import Question, QuestionOption
from ..models.final_quiz import FinalQuiz
from ..schemas.question import QuestionCreate, QuestionResponse, QuestionsListResponse


class QuestionCRUD:
    """CRUD operations for Questions with backward compatibility"""
    
    @staticmethod
    async def get_questions_by_lesson(
        db: AsyncSession, 
        lesson_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> QuestionsListResponse:
        """Get questions by lesson_id (new approach)"""
        
        # Query questions directly by lesson_id
        query = (
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.question_type_relation)
            )
            .filter(Question.lesson_id == lesson_id)
            .order_by(Question.order_index)
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        questions = result.scalars().all()
        
        # Count total
        count_query = select(Question).filter(Question.lesson_id == lesson_id)
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        return QuestionsListResponse(
            questions=[QuestionResponse.model_validate(q) for q in questions],
            total=total,
            lesson_id=lesson_id
        )
    
    @staticmethod
    async def get_questions_by_quiz(
        db: AsyncSession, 
        quiz_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> QuestionsListResponse:
        """Get questions by quiz_id (backward compatibility)"""
        
        # Query questions by quiz_id
        query = (
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.question_type_relation)
            )
            .filter(Question.quiz_id == quiz_id)
            .order_by(Question.order_index)
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        questions = result.scalars().all()
        
        # Count total
        count_query = select(Question).filter(Question.quiz_id == quiz_id)
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        return QuestionsListResponse(
            questions=[QuestionResponse.model_validate(q) for q in questions],
            total=total,
            quiz_id=quiz_id
        )
    
    @staticmethod
    async def get_questions_flexible(
        db: AsyncSession,
        lesson_id: Optional[int] = None,
        quiz_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> QuestionsListResponse:
        """Get questions by either lesson_id or quiz_id (flexible approach)"""
        
        if lesson_id and quiz_id:
            # Both provided - query by lesson_id (preferred)
            return await QuestionCRUD.get_questions_by_lesson(db, lesson_id, skip, limit)
        elif lesson_id:
            return await QuestionCRUD.get_questions_by_lesson(db, lesson_id, skip, limit)
        elif quiz_id:
            return await QuestionCRUD.get_questions_by_quiz(db, quiz_id, skip, limit)
        else:
            raise ValueError("Either lesson_id or quiz_id must be provided")
    
    @staticmethod
    async def create_question(
        db: AsyncSession,
        question_data: QuestionCreate
    ) -> QuestionResponse:
        """Create a new question with backward compatibility"""
        
        # Validate that either lesson_id or quiz_id is provided
        if not question_data.lesson_id and not question_data.quiz_id:
            raise ValueError("Either lesson_id or quiz_id must be provided")
        
        # Create question
        question = Question(
            lesson_id=question_data.lesson_id,
            quiz_id=question_data.quiz_id,
            question_type=question_data.question_type,
            question_type_id=question_data.question_type_id,
            content=question_data.content,
            audio_url=question_data.audio_url,
            image_url=question_data.image_url,
            correct_answer=question_data.correct_answer,
            explanation=question_data.explanation,
            order_index=question_data.order_index
        )
        
        db.add(question)
        await db.flush()  # Get the ID
        
        # Create options if provided
        if question_data.options:
            for option_data in question_data.options:
                option = QuestionOption(
                    question_id=question.id,
                    option_text=option_data.option_text,
                    is_correct=option_data.is_correct,
                    order_index=option_data.order_index
                )
                db.add(option)
        
        await db.commit()
        await db.refresh(question)
        
        return QuestionResponse.model_validate(question)
    
    @staticmethod
    async def get_question_by_id(
        db: AsyncSession,
        question_id: int
    ) -> Optional[QuestionResponse]:
        """Get a single question by ID"""
        
        query = (
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.question_type_relation)
            )
            .filter(Question.id == question_id)
        )
        
        result = await db.execute(query)
        question = result.scalar_one_or_none()
        
        if question:
            return QuestionResponse.model_validate(question)
        return None


class FinalQuizCRUD:
    """CRUD operations for FinalQuiz"""
    
    @staticmethod
    async def get_final_quiz_by_unit(
        db: AsyncSession,
        unit_id: int
    ) -> Optional[dict]:
        """Get final quiz for a unit with questions"""
        
        # Get final quiz
        quiz_query = select(FinalQuiz).filter(FinalQuiz.unit_id == unit_id)
        quiz_result = await db.execute(quiz_query)
        quiz = quiz_result.scalar_one_or_none()
        
        if not quiz:
            return None
        
        # Get questions for this quiz
        questions_query = (
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.question_type_relation)
            )
            .filter(Question.quiz_id == quiz.id)
            .order_by(Question.order_index)
        )
        
        questions_result = await db.execute(questions_query)
        questions = questions_result.scalars().all()
        
        # Format response
        quiz_data = {
            "id": quiz.id,
            "unit_id": quiz.unit_id,
            "title": quiz.title,
            "description": quiz.description,
            "type": quiz.type,
            "order_index": quiz.order_index,
            "created_at": quiz.created_at,
            "questions": [
                {
                    "id": q.id,
                    "content": q.content,
                    "audio_url": q.audio_url,
                    "image_url": q.image_url,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "order_index": q.order_index,
                    "question_type": q.question_type,
                    "options": [
                        {
                            "id": opt.id,
                            "option_text": opt.option_text,
                            "is_correct": opt.is_correct,
                            "order_index": opt.order_index
                        }
                        for opt in q.options
                    ]
                }
                for q in questions
            ]
        }
        
        return quiz_data
