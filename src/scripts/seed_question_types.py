import asyncio
import logging

from sqlalchemy import select

from ..app.core.db.database import AsyncSession, local_session
from ..app.models.question_type import QuestionType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define the question types to seed
QUESTION_TYPES = [
    {
        "code": "MULTIPLE_CHOICE",
        "name": "Multiple Choice",
        "description": "Question with multiple options, one correct answer"
    },
    {
        "code": "MATCHING",
        "name": "Matching",
        "description": "Match items from two lists"
    },
    {
        "code": "SENTENCE_ORDER",
        "name": "Sentence Order",
        "description": "Arrange sentences in correct order"
    },
    {
        "code": "AUDIO_COMPREHENSION",
        "name": "Audio Comprehension",
        "description": "Listen to audio and answer questions"
    },
    {
        "code": "PRONUNCIATION",
        "name": "Pronunciation",
        "description": "Practice pronunciation"
    },
    {
        "code": "BLANK",
        "name": "Fill in the Blank",
        "description": "Fill in missing words"
    }
]


async def seed_question_types(session: AsyncSession) -> None:
    """Seed question types into database."""
    try:
        # Check if types already exist
        query = select(QuestionType)
        result = await session.execute(query)
        existing_types = result.scalars().all()
        
        if existing_types:
            logger.info(f"Found {len(existing_types)} existing question types. Skipping seed.")
            return
        
        # Create all question types
        for type_data in QUESTION_TYPES:
            question_type = QuestionType(**type_data)
            session.add(question_type)
        
        await session.commit()
        logger.info(f"Successfully seeded {len(QUESTION_TYPES)} question types.")
        
    except Exception as e:
        logger.error(f"Error seeding question types: {e}")
        raise


async def main():
    """Main entry point."""
    async with local_session() as session:
        await seed_question_types(session)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

