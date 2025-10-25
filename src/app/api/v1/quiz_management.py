# src/app/api/v1/quiz_management.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.quiz import Quiz, Question, QuestionOption, QuestionType
from ...models.exercise import ListeningExercise, SpeakingExercise, WritingExercise
from ...models.user import User
from ...models.progress import UserQuizAttempt, UserQuestionAttempt, UserQuestionError

router = APIRouter(tags=["quiz_exercises"])


# UC3: Take Quiz / Exercises
@router.get("/quizzes/{quiz_id}", response_model=dict)
async def get_quiz(
    request: Request,
    quiz_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get quiz details with questions and options"""
    
    # Get quiz with questions and options
    quiz_query = select(Quiz).options(
        selectinload(Quiz.questions).selectinload(Question.options),
        selectinload(Quiz.questions).selectinload(Question.question_type)
    ).filter(Quiz.id == quiz_id)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalar_one_or_none()
    
    if not quiz:
        raise NotFoundException("Quiz not found")
    
    # Get questions with options
    questions_data = []
    for question in quiz.questions:
        question_dict = {
            "id": question.id,
            "content": question.content,
            "audio_url": question.audio_url,
            "image_url": question.image_url,
            "explanation": question.explanation,
            "order_index": question.order_index,
            "question_type": {
                "id": question.question_type.id,
                "name": question.question_type.name,
                "description": question.question_type.description
            },
            "options": [
                {
                    "id": option.id,
                    "option_text": option.option_text,
                    "is_correct": option.is_correct
                }
                for option in question.options
            ]
        }
        questions_data.append(question_dict)
    
    return {
        "id": quiz.id,
        "lesson_id": quiz.lesson_id,
        "title": quiz.title,
        "description": quiz.description,
        "type": quiz.type,
        "order_index": quiz.order_index,
        "created_at": quiz.created_at,
        "questions": questions_data
    }


@router.post("/quizzes/{quiz_id}/attempt", response_model=dict)
async def submit_quiz_attempt(
    request: Request,
    quiz_id: int,
    answers: dict,  # {"question_id": "user_answer"}
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Submit quiz answers and get results"""
    
    quiz_query = select(Quiz).filter(Quiz.id == quiz_id)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalar_one_or_none()
    
    if not quiz:
        raise NotFoundException("Quiz not found")
    
    # Create quiz attempt
    quiz_attempt = UserQuizAttempt(
        user_id=current_user["id"],
        quiz_id=quiz_id,
        started_at=datetime.now(UTC)
    )
    db.add(quiz_attempt)
    db.commit()
    db.refresh(quiz_attempt)
    
    # Process answers and calculate score
    correct_answers = 0
    total_questions = len(quiz.questions)
    question_attempts = []
    
    for question in quiz.questions:
        user_answer = answers.get(str(question.id), "")
        is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
        
        if is_correct:
            correct_answers += 1
        
        # Create question attempt
        question_attempt = UserQuestionAttempt(
            user_quiz_attempt_id=quiz_attempt.id,
            question_id=question.id,
            user_answer=user_answer,
            is_correct=is_correct
        )
        db.add(question_attempt)
        question_attempts.append(question_attempt)
        
        # Update or create question error record for incorrect answers
        if not is_correct:
            error_query = select(UserQuestionError).filter(
                UserQuestionError.user_id == current_user["id"],
                UserQuestionError.question_id == question.id
            )
            error_result = await db.execute(error_query)
            error_record = error_result.scalar_one_or_none()
            
            if error_record:
                error_record.last_wrong_answer = user_answer
                error_record.last_wrong_at = datetime.now(UTC)
                error_record.error_count += 1
            else:
                error_record = UserQuestionError(
                    user_id=current_user["id"],
                    question_id=question.id,
                    last_wrong_answer=user_answer,
                    last_wrong_at=datetime.now(UTC),
                    error_count=1
                )
                db.add(error_record)
    
    # Calculate score and EXP
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    exp_earned = int(score / 10) * 10  # 10 EXP per 10% score
    
    # Update quiz attempt
    quiz_attempt.score = score
    quiz_attempt.exp_earned = exp_earned
    quiz_attempt.completed_at = datetime.now(UTC)
    
    # Update user EXP
    user_query = select(User).filter(User.id == current_user["id"])
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if user:
        user.exp += exp_earned
    
    db.commit()
    
    return {
        "quiz_attempt_id": quiz_attempt.id,
        "score": score,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "exp_earned": exp_earned,
        "completed_at": quiz_attempt.completed_at,
        "question_results": [
            {
                "question_id": attempt.question_id,
                "user_answer": attempt.user_answer,
                "is_correct": attempt.is_correct
            }
            for attempt in question_attempts
        ]
    }


@router.get("/exercises/listening/{exercise_id}", response_model=dict)
async def get_listening_exercise(
    request: Request,
    exercise_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get listening exercise details"""
    exercise_query = select(ListeningExercise).filter(ListeningExercise.id == exercise_id)
    exercise_result = await db.execute(exercise_query)
    exercise = exercise_result.scalar_one_or_none()
    if not exercise:
        raise NotFoundException("Listening exercise not found")
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "audio_url": exercise.audio_url,
        "description": exercise.description,
        "created_at": exercise.created_at
    }


@router.get("/exercises/speaking/{exercise_id}", response_model=dict)
async def get_speaking_exercise(
    request: Request,
    exercise_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get speaking exercise details"""
    exercise_query = select(SpeakingExercise).filter(SpeakingExercise.id == exercise_id)
    exercise_result = await db.execute(exercise_query)
    exercise = exercise_result.scalar_one_or_none()
    if not exercise:
        raise NotFoundException("Speaking exercise not found")
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "prompt": exercise.prompt,
        "sample_answer": exercise.sample_answer,
        "created_at": exercise.created_at
    }


@router.get("/exercises/writing/{exercise_id}", response_model=dict)
async def get_writing_exercise(
    request: Request,
    exercise_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get writing exercise details"""
    exercise_query = select(WritingExercise).filter(WritingExercise.id == exercise_id)
    exercise_result = await db.execute(exercise_query)
    exercise = exercise_result.scalar_one_or_none()
    if not exercise:
        raise NotFoundException("Writing exercise not found")
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "prompt": exercise.prompt,
        "sample_answer": exercise.sample_answer,
        "created_at": exercise.created_at
    }


@router.get("/user/{username}/quiz-attempts", response_model=PaginatedListResponse[dict])
async def get_user_quiz_attempts(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's quiz attempts (own attempts or admin view)"""
    
    # Check if user can view these attempts
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own quiz attempts")
    
    user_query = select(User).filter(User.username == username)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    attempts_query = select(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user.id
    ).order_by(UserQuizAttempt.started_at.desc())
    
    attempts_result = await db.execute(attempts_query.offset(offset).limit(items_per_page))
    attempts = attempts_result.scalars().all()
    
    total_result = await db.execute(select(func.count()).select_from(UserQuizAttempt).filter(UserQuizAttempt.user_id == user.id))
    total = total_result.scalar()
    
    attempts_data = []
    for attempt in attempts:
        attempt_dict = {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "quiz_title": attempt.quiz.title if attempt.quiz else None,
            "score": attempt.score,
            "exp_earned": attempt.exp_earned,
            "started_at": attempt.started_at,
            "completed_at": attempt.completed_at
        }
        attempts_data.append(attempt_dict)
    
    response = paginated_response(
        crud_data={"data": attempts_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


# Admin endpoints for UC15: Manage Quizzes
@router.post("/quizzes", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_quiz(
    request: Request,
    quiz_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new quiz (Admin only)"""
    quiz = Quiz(
        lesson_id=quiz_data["lesson_id"],
        title=quiz_data["title"],
        description=quiz_data["description"],
        type=quiz_data["type"],
        order_index=quiz_data.get("order_index", 0)
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    return {
        "id": quiz.id,
        "lesson_id": quiz.lesson_id,
        "title": quiz.title,
        "description": quiz.description,
        "type": quiz.type,
        "order_index": quiz.order_index,
        "created_at": quiz.created_at
    }


@router.post("/quizzes/{quiz_id}/questions", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_question(
    request: Request,
    quiz_id: int,
    question_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new question for a quiz (Admin only)"""
    quiz_query = select(Quiz).filter(Quiz.id == quiz_id)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise NotFoundException("Quiz not found")
    
    question = Question(
        quiz_id=quiz_id,
        question_type_id=question_data["question_type_id"],
        content=question_data["content"],
        audio_url=question_data.get("audio_url"),
        image_url=question_data.get("image_url"),
        correct_answer=question_data["correct_answer"],
        explanation=question_data["explanation"],
        order_index=question_data.get("order_index", 0)
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    
    # Add options if provided
    if "options" in question_data:
        for option_data in question_data["options"]:
            option = QuestionOption(
                question_id=question.id,
                option_text=option_data["option_text"],
                is_correct=option_data.get("is_correct", False)
            )
            db.add(option)
    
    db.commit()
    
    return {
        "id": question.id,
        "quiz_id": question.quiz_id,
        "content": question.content,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "order_index": question.order_index,
        "created_at": question.created_at
    }


@router.post("/exercises/listening", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_listening_exercise(
    request: Request,
    exercise_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new listening exercise (Admin only)"""
    exercise = ListeningExercise(
        lesson_id=exercise_data["lesson_id"],
        audio_url=exercise_data["audio_url"],
        transcript=exercise_data["transcript"],
        description=exercise_data["description"]
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "audio_url": exercise.audio_url,
        "transcript": exercise.transcript,
        "description": exercise.description,
        "created_at": exercise.created_at
    }


@router.post("/exercises/speaking", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_speaking_exercise(
    request: Request,
    exercise_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new speaking exercise (Admin only)"""
    exercise = SpeakingExercise(
        lesson_id=exercise_data["lesson_id"],
        prompt=exercise_data["prompt"],
        sample_answer=exercise_data["sample_answer"]
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "prompt": exercise.prompt,
        "sample_answer": exercise.sample_answer,
        "created_at": exercise.created_at
    }


@router.post("/exercises/writing", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_writing_exercise(
    request: Request,
    exercise_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new writing exercise (Admin only)"""
    exercise = WritingExercise(
        lesson_id=exercise_data["lesson_id"],
        prompt=exercise_data["prompt"],
        sample_answer=exercise_data["sample_answer"]
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    
    return {
        "id": exercise.id,
        "lesson_id": exercise.lesson_id,
        "prompt": exercise.prompt,
        "sample_answer": exercise.sample_answer,
        "created_at": exercise.created_at
    }
