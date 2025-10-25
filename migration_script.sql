-- Migration Script for Korean Learning App Database Restructure
-- This script updates the database to support the new course structure:
-- Lesson -> Questions (practice questions)
-- Unit -> Quiz (final unit test)

-- Step 1: Add lesson_id column to questions table
ALTER TABLE questions ADD COLUMN lesson_id INTEGER;

-- Step 2: Add question_type column to questions table
ALTER TABLE questions ADD COLUMN question_type VARCHAR(50) DEFAULT 'practice';

-- Step 3: Add unit_id column to quizzes table (for final unit tests)
ALTER TABLE quizzes ADD COLUMN unit_id INTEGER;

-- Step 4: Add foreign key constraints
ALTER TABLE questions ADD CONSTRAINT fk_questions_lesson_id 
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE;

ALTER TABLE quizzes ADD CONSTRAINT fk_quizzes_unit_id 
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE;

-- Step 5: Migrate existing quiz questions to lesson questions
-- This will move all questions from quizzes to their parent lessons
UPDATE questions 
SET lesson_id = (
    SELECT lesson_id 
    FROM quizzes 
    WHERE quizzes.id = questions.quiz_id
)
WHERE quiz_id IS NOT NULL;

-- Step 6: Update question_type for migrated questions
UPDATE questions 
SET question_type = 'practice'
WHERE lesson_id IS NOT NULL AND question_type = 'practice';

-- Step 7: Create indexes for better performance
CREATE INDEX idx_questions_lesson_id ON questions(lesson_id);
CREATE INDEX idx_questions_question_type ON questions(question_type);
CREATE INDEX idx_quizzes_unit_id ON quizzes(unit_id);

-- Step 8: Update existing quizzes to be unit-level (final tests)
-- This assumes existing quizzes should become unit tests
-- You may need to adjust this based on your specific data
UPDATE quizzes 
SET unit_id = (
    SELECT unit_id 
    FROM lessons 
    WHERE lessons.id = quizzes.lesson_id
),
type = 'unit_test'
WHERE lesson_id IS NOT NULL;

-- Step 9: Make lesson_id nullable in questions (since some questions might still belong to quizzes)
ALTER TABLE questions ALTER COLUMN lesson_id DROP NOT NULL;

-- Step 10: Add comments for documentation
COMMENT ON COLUMN questions.lesson_id IS 'Reference to lesson for practice questions';
COMMENT ON COLUMN questions.question_type IS 'Type of question: practice, assessment, listening, speaking, writing';
COMMENT ON COLUMN quizzes.unit_id IS 'Reference to unit for final unit tests';
COMMENT ON COLUMN quizzes.type IS 'Type of quiz: unit_test, lesson_test, etc.';

-- Step 11: Create a view for easier querying of lesson content
CREATE OR REPLACE VIEW lesson_content AS
SELECT 
    l.id as lesson_id,
    l.title as lesson_title,
    l.description as lesson_description,
    l.order_index as lesson_order,
    u.id as unit_id,
    u.title as unit_title,
    c.id as course_id,
    c.title as course_title,
    -- Practice questions
    COALESCE(
        (SELECT COUNT(*) 
         FROM questions q 
         WHERE q.lesson_id = l.id AND q.question_type = 'practice'), 
        0
    ) as practice_questions_count,
    -- Listening exercises
    COALESCE(
        (SELECT COUNT(*) 
         FROM listening_exercises le 
         WHERE le.lesson_id = l.id), 
        0
    ) as listening_exercises_count,
    -- Speaking exercises
    COALESCE(
        (SELECT COUNT(*) 
         FROM speaking_exercises se 
         WHERE se.lesson_id = l.id), 
        0
    ) as speaking_exercises_count,
    -- Writing exercises
    COALESCE(
        (SELECT COUNT(*) 
         FROM writing_exercises we 
         WHERE we.lesson_id = l.id), 
        0
    ) as writing_exercises_count,
    -- Unit test quiz
    COALESCE(
        (SELECT COUNT(*) 
         FROM quizzes q 
         WHERE q.unit_id = u.id AND q.type = 'unit_test'), 
        0
    ) as unit_test_quiz_count
FROM lessons l
JOIN units u ON l.unit_id = u.id
JOIN courses c ON u.course_id = c.id;

-- Step 12: Create a view for unit test quizzes
CREATE OR REPLACE VIEW unit_test_quizzes AS
SELECT 
    q.id as quiz_id,
    q.title as quiz_title,
    q.description as quiz_description,
    q.type as quiz_type,
    u.id as unit_id,
    u.title as unit_title,
    c.id as course_id,
    c.title as course_title,
    COUNT(qu.id) as questions_count
FROM quizzes q
JOIN units u ON q.unit_id = u.id
JOIN courses c ON u.course_id = c.id
LEFT JOIN questions qu ON qu.quiz_id = q.id
WHERE q.type = 'unit_test'
GROUP BY q.id, q.title, q.description, q.type, u.id, u.title, c.id, c.title;

-- Migration completed successfully
-- The database now supports:
-- 1. Questions directly linked to lessons (practice questions)
-- 2. Quizzes linked to units (final unit tests)
-- 3. Mixed content types within lessons (questions + exercises)
-- 4. Backward compatibility with existing quiz system
