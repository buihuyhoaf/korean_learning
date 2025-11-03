"""
CRUD Operations for Questions

Provides database operations for creating, reading, updating, and deleting questions
with support for all 9 question types and their subtype relationships.
"""
from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.question_type import QuestionType
from ..models.question import Question
from ..models.question_option import QuestionOption
from ..models.question_matching_pair import QuestionMatchingPair
from ..models.question_sentence_order import QuestionSentenceOrder
from ..models.question_audio_comprehension import QuestionAudioComprehension
from ..models.question_pronunciation import QuestionPronunciation
from ..models.question_blank import QuestionBlank
from ..models.course import Lesson
from ..schemas.question_schemas import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionsListResponse
)


class QuestionCRUD:
    """CRUD operations for Questions with support for 9 question types."""
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        question_id: int,
        include_subtypes: bool = True
    ) -> Optional[Question]:
        """
        Get a question by ID with all relationships loaded.
        
        Args:
            db: Database session
            question_id: ID of the question
            include_subtypes: Whether to load subtype relationships
            
        Returns:
            Question object or None if not found
        """
        query = select(Question).filter(Question.id == question_id)
        
        if include_subtypes:
            query = query.options(
                selectinload(Question.question_type_relation),
                selectinload(Question.options),
                selectinload(Question.matching_pairs),
                selectinload(Question.sentence_order),
                selectinload(Question.audio_comprehension),
                selectinload(Question.pronunciation),
                selectinload(Question.blanks),
                selectinload(Question.lesson)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_lesson(
        db: AsyncSession,
        lesson_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> QuestionsListResponse:
        """
        Get all questions for a lesson with subtype data loaded.
        
        Args:
            db: Database session
            lesson_id: ID of the lesson
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            QuestionsListResponse with questions and total count
        """
        # Query questions
        query = (
            select(Question)
            .options(
                selectinload(Question.question_type_relation),
                selectinload(Question.options),
                selectinload(Question.matching_pairs),
                selectinload(Question.sentence_order),
                selectinload(Question.audio_comprehension),
                selectinload(Question.pronunciation),
                selectinload(Question.blanks),
                selectinload(Question.lesson)
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
    async def create(
        db: AsyncSession,
        question_data: QuestionCreate
    ) -> QuestionResponse:
        """
        Create a new question with subtype data based on question type.
        
        Args:
            db: Database session
            question_data: Question creation data
            
        Returns:
            Created question as QuestionResponse
        """
        # Verify question type exists
        type_query = select(QuestionType).filter(QuestionType.id == question_data.question_type_id)
        type_result = await db.execute(type_query)
        question_type = type_result.scalar_one_or_none()
        if not question_type:
            raise ValueError(f"Question type with id {question_data.question_type_id} not found")
        
        # Verify lesson exists
        lesson_query = select(Lesson).filter(Lesson.id == question_data.lesson_id)
        lesson_result = await db.execute(lesson_query)
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson with id {question_data.lesson_id} not found")
        
        # Auto-increment order_index if not provided
        order_index = question_data.order_index
        if order_index is None:
            # Get max order_index for this lesson
            max_order_query = select(func.max(Question.order_index)).filter(
                Question.lesson_id == question_data.lesson_id
            )
            max_order_result = await db.execute(max_order_query)
            max_order = max_order_result.scalar() or -1
            order_index = max_order + 1
        
        # Create main question
        question = Question(
            question_type_id=question_data.question_type_id,
            lesson_id=question_data.lesson_id,
            content=question_data.content,
            media=question_data.media,
            question_metadata=question_data.question_metadata,
            explanation=question_data.explanation,
            order_index=order_index
        )
        
        db.add(question)
        await db.flush()  # Get the ID
        
        # Create subtype data based on question type code
        type_code = question_type.code.upper()
        
        if type_code == "MULTIPLE_CHOICE" and question_data.options:
            # Create options
            for opt_data in question_data.options:
                option = QuestionOption(
                    question_id=question.id,
                    option_text=opt_data.option_text,
                    option_media=opt_data.option_media,
                    is_correct=opt_data.is_correct,
                    sort_order=opt_data.sort_order
                )
                db.add(option)
        
        elif type_code == "MATCHING" and question_data.matching_pairs:
            # Create matching pairs
            for pair_data in question_data.matching_pairs:
                pair = QuestionMatchingPair(
                    question_id=question.id,
                    left_text=pair_data.left_text,
                    left_media=pair_data.left_media,
                    right_text=pair_data.right_text,
                    right_media=pair_data.right_media,
                    sort_order=pair_data.sort_order
                )
                db.add(pair)
        
        elif type_code == "SENTENCE_ORDER" and question_data.sentence_order:
            # Create sentence order
            sentence_order = QuestionSentenceOrder(
                question_id=question.id,
                correct_sequence=question_data.sentence_order.correct_sequence
            )
            db.add(sentence_order)
        
        elif type_code == "AUDIO_COMPREHENSION" and question_data.audio_comprehension:
            # Create audio comprehension
            audio_comp = QuestionAudioComprehension(
                question_id=question.id,
                transcript=question_data.audio_comprehension.transcript,
                tts_config=question_data.audio_comprehension.tts_config
            )
            db.add(audio_comp)
        
        elif type_code == "PRONUNCIATION" and question_data.pronunciation:
            # Create pronunciation
            pronunciation = QuestionPronunciation(
                question_id=question.id,
                target_phrase=question_data.pronunciation.target_phrase,
                reference_audio_url=question_data.pronunciation.reference_audio_url,
                tts_config=question_data.pronunciation.tts_config
            )
            db.add(pronunciation)
        
        elif type_code == "BLANK" and question_data.blank:
            # Create blank
            blank = QuestionBlank(
                question_id=question.id,
                correct_answer=question_data.blank.correct_answer,
                case_sensitive=question_data.blank.case_sensitive
            )
            db.add(blank)
        
        await db.commit()
        await db.refresh(question)
        
        # Reload with relationships
        return QuestionResponse.model_validate(
            await QuestionCRUD.get_by_id(db, question.id, include_subtypes=True)
        )
    
    @staticmethod
    async def update(
        db: AsyncSession,
        question_id: int,
        question_data: QuestionUpdate
    ) -> Optional[QuestionResponse]:
        """
        Update a question.
        
        Args:
            db: Database session
            question_id: ID of the question to update
            question_data: Update data
            
        Returns:
            Updated question as QuestionResponse or None if not found
        """
        question = await QuestionCRUD.get_by_id(db, question_id, include_subtypes=False)
        if not question:
            return None
        
        # Update fields
        if question_data.content is not None:
            question.content = question_data.content
        if question_data.media is not None:
            question.media = question_data.media
        if question_data.question_metadata is not None:
            question.question_metadata = question_data.question_metadata
        if question_data.explanation is not None:
            question.explanation = question_data.explanation
        if question_data.order_index is not None:
            question.order_index = question_data.order_index
        if question_data.lesson_id is not None:
            question.lesson_id = question_data.lesson_id
        
        await db.commit()
        await db.refresh(question)
        
        # Reload with relationships
        return QuestionResponse.model_validate(
            await QuestionCRUD.get_by_id(db, question.id, include_subtypes=True)
        )
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        question_id: int
    ) -> bool:
        """
        Delete a question (cascade deletes all subtype data).
        
        Args:
            db: Database session
            question_id: ID of the question to delete
            
        Returns:
            True if deleted, False if not found
        """
        question = await QuestionCRUD.get_by_id(db, question_id, include_subtypes=False)
        if not question:
            return False
        
        await db.delete(question)
        await db.commit()
        return True
    
    @staticmethod
    async def get_question_type_by_code(
        db: AsyncSession,
        code: str
    ) -> Optional[QuestionType]:
        """
        Get question type by code.
        
        Args:
            db: Database session
            code: Question type code (e.g., 'MULTIPLE_CHOICE')
            
        Returns:
            QuestionType or None if not found
        """
        query = select(QuestionType).filter(QuestionType.code == code.upper())
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_question_types(
        db: AsyncSession
    ) -> List[QuestionType]:
        """
        List all question types.
        
        Args:
            db: Database session
            
        Returns:
            List of QuestionType objects
        """
        query = select(QuestionType).order_by(QuestionType.id)
        result = await db.execute(query)
        return list(result.scalars().all())
