"""
CRUD Operations for User Answers

Provides database operations for submitting answers and evaluating correctness
for different question types.
"""
from typing import Optional, List
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.question import Question
from ..models.question_option import QuestionOption
from ..models.question_matching_pair import QuestionMatchingPair
from ..models.question_sentence_order import QuestionSentenceOrder
from ..models.question_blank import QuestionBlank
from ..models.user_answer import UserAnswer
from ..schemas.answer_schemas import AnswerSubmitRequest, AnswerSubmitResponse, AnswerResponse


class AnswerCRUD:
    """CRUD operations for User Answers with automatic correctness evaluation."""
    
    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        user_id: int,
        question_id: int,
        answer_data: AnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        """
        Submit an answer and automatically evaluate correctness.
        
        Args:
            db: Database session
            user_id: ID of the user submitting the answer
            question_id: ID of the question
            answer_data: Answer submission data
            
        Returns:
            AnswerSubmitResponse with evaluation results
        """
        # Get question with all relationships
        question_query = (
            select(Question)
            .options(
                selectinload(Question.question_type_relation),
                selectinload(Question.options),
                selectinload(Question.matching_pairs),
                selectinload(Question.sentence_order),
                selectinload(Question.blanks)
            )
            .filter(Question.id == question_id)
        )
        result = await db.execute(question_query)
        question = result.scalar_one_or_none()
        
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        
        # Evaluate answer based on question type
        evaluation = await AnswerCRUD._evaluate_answer(db, question, answer_data.answer)
        
        # Create user answer record
        user_answer = UserAnswer(
            user_id=user_id,
            question_id=question_id,
            answer=answer_data.answer,
            is_correct=evaluation["is_correct"],
            score=evaluation["score"]
        )
        
        db.add(user_answer)
        await db.commit()
        await db.refresh(user_answer)
        
        return AnswerSubmitResponse(
            answer_id=user_answer.id,
            is_correct=evaluation["is_correct"],
            score=evaluation["score"],
            feedback=evaluation.get("feedback"),
            correct_answer=evaluation.get("correct_answer"),
            explanation=question.explanation
        )
    
    @staticmethod
    async def _evaluate_answer(
        db: AsyncSession,
        question: Question,
        user_answer: any
    ) -> dict:
        """
        Evaluate answer correctness based on question type.
        
        Args:
            db: Database session
            question: Question object with relationships loaded
            user_answer: User's answer (flexible JSON structure)
            
        Returns:
            Dictionary with is_correct, score, feedback, and correct_answer
        """
        type_code = question.question_type_relation.code.upper()
        
        if type_code == "MULTIPLE_CHOICE":
            # User answer should be a list of option IDs
            if not isinstance(user_answer, list):
                return {"is_correct": False, "score": 0.0, "feedback": "Invalid answer format"}
            
            # Get correct option IDs
            correct_option_ids = [opt.id for opt in question.options if opt.is_correct]
            
            # Check if user selected exactly the correct options
            user_selected = set(user_answer)
            correct_selected = set(correct_option_ids)
            
            is_correct = user_selected == correct_selected and len(user_selected) > 0
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "correct_answer": correct_option_ids,
                "feedback": "Correct!" if is_correct else "Incorrect. Please try again."
            }
        
        elif type_code == "BLANK":
            if not question.blanks:
                return {"is_correct": False, "score": 0.0, "feedback": "Question data incomplete"}
            
            blank = question.blanks
            user_text = str(user_answer) if not isinstance(user_answer, str) else user_answer
            
            if blank.case_sensitive:
                is_correct = user_text.strip() == blank.correct_answer.strip()
            else:
                is_correct = user_text.strip().lower() == blank.correct_answer.strip().lower()
            
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "correct_answer": blank.correct_answer,
                "feedback": "Correct!" if is_correct else f"Correct answer: {blank.correct_answer}"
            }
        
        elif type_code == "SENTENCE_ORDER":
            if not question.sentence_order:
                return {"is_correct": False, "score": 0.0, "feedback": "Question data incomplete"}
            
            if not isinstance(user_answer, list):
                return {"is_correct": False, "score": 0.0, "feedback": "Invalid answer format"}
            
            correct_sequence = question.sentence_order.correct_sequence
            user_sequence = [str(item) for item in user_answer]
            correct_sequence_str = [str(item) for item in correct_sequence]
            
            is_correct = user_sequence == correct_sequence_str
            
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "correct_answer": correct_sequence,
                "feedback": "Correct order!" if is_correct else "Incorrect order. Please try again."
            }
        
        elif type_code == "MATCHING":
            if not isinstance(user_answer, dict):
                return {"is_correct": False, "score": 0.0, "feedback": "Invalid answer format"}
            
            # Evaluate matching pairs
            # For simplicity, we'll check if all pairs match correctly
            # In a real implementation, you might want more sophisticated scoring
            total_pairs = len(question.matching_pairs)
            if total_pairs == 0:
                return {"is_correct": False, "score": 0.0, "feedback": "Question data incomplete"}
            
            # This is a simplified evaluation - you might need to adapt based on your matching logic
            # For now, we'll just check if the structure is valid
            is_correct = len(user_answer) == total_pairs
            score = 0.5 if is_correct else 0.0  # Partial credit, implement full logic as needed
            
            return {
                "is_correct": is_correct,
                "score": score,
                "feedback": "All pairs matched!" if is_correct else "Some pairs are incorrect."
            }
        
        elif type_code in ["AUDIO_COMPREHENSION", "PRONUNCIATION"]:
            # These types typically require manual evaluation or AI-based evaluation
            # For now, return a placeholder response
            return {
                "is_correct": None,  # Requires manual/AI evaluation
                "score": None,
                "feedback": "Answer submitted. Evaluation pending."
            }
        
        else:
            # Unknown question type - cannot evaluate
            return {
                "is_correct": None,
                "score": None,
                "feedback": f"Cannot automatically evaluate question type: {type_code}"
            }
    
    @staticmethod
    async def get_user_answer(
        db: AsyncSession,
        user_id: int,
        question_id: int
    ) -> Optional[AnswerResponse]:
        """
        Get user's answer for a specific question.
        
        Args:
            db: Database session
            user_id: ID of the user
            question_id: ID of the question
            
        Returns:
            AnswerResponse or None if not found
        """
        query = (
            select(UserAnswer)
            .filter(
                and_(
                    UserAnswer.user_id == user_id,
                    UserAnswer.question_id == question_id
                )
            )
            .order_by(desc(UserAnswer.answered_at))
            .limit(1)
        )
        
        result = await db.execute(query)
        answer = result.scalar_one_or_none()
        
        if answer:
            return AnswerResponse.model_validate(answer)
        return None
    
    @staticmethod
    async def get_user_answer_history(
        db: AsyncSession,
        user_id: int,
        question_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AnswerResponse]:
        """
        Get user's answer history.
        
        Args:
            db: Database session
            user_id: ID of the user
            question_id: Optional filter by question ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of AnswerResponse objects
        """
        query = select(UserAnswer).filter(UserAnswer.user_id == user_id)
        
        if question_id:
            query = query.filter(UserAnswer.question_id == question_id)
        
        query = query.order_by(desc(UserAnswer.answered_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        answers = result.scalars().all()
        
        return [AnswerResponse.model_validate(answer) for answer in answers]

