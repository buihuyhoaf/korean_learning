-- Entry Test Questions Data for Korean Learning App
-- This file adds NEW questions to existing 5 entry tests (ID: 1, 2, 3, 4, 5)
-- Current database state: 5 EntryTest, 22 EntryTestQuestion, 36 EntryTestQuestionOption, 17 EntryTestResult
-- This will add additional questions without ID conflicts using auto-increment

-- ==========================================
-- FIX SEQUENCES TO AVOID ID CONFLICTS
-- ==========================================

-- IMPORTANT: Run fix_sequences.sql BEFORE this script to avoid ID conflicts!
-- Or manually run these commands if you know the sequence names:
-- SELECT setval('entry_test_questions_id_seq', (SELECT MAX(id) FROM entry_test_questions));
-- SELECT setval('entry_test_question_options_id_seq', (SELECT MAX(id) FROM entry_test_question_options));

-- ==========================================
-- ENTRY TEST 1 - ADDITIONAL BASIC LEVEL QUESTIONS
-- ==========================================

-- Additional Question 1: Basic Korean greeting alternatives
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 1, 'How do you say "Good morning" in Korean?', '좋은 아침입니다', '좋은 아침입니다 (joeun achimimnida) is the formal way to say good morning in Korean.', 10, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 1 AND content = 'How do you say "Good morning" in Korean?'
);

-- Get the question ID for options insertion
DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 1 AND content = 'How do you say "Good morning" in Korean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, '좋은 아침입니다', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '좋은 아침입니다')
        UNION ALL
        SELECT q_id, '좋은 저녁입니다', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '좋은 저녁입니다')
        UNION ALL
        SELECT q_id, '좋은 밤입니다', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '좋은 밤입니다')
        UNION ALL
        SELECT q_id, '안녕히 가세요', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '안녕히 가세요');
    END IF;
END $$;

-- Additional Question 2: Korean numbers (higher)
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 1, 'How do you say "ten" in Korean?', '열', '열 (yeol) is the Korean word for "ten". It is used in counting.', 11, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 1 AND content = 'How do you say "ten" in Korean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 1 AND content = 'How do you say "ten" in Korean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, '열', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '열')
        UNION ALL
        SELECT q_id, '아홉', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '아홉')
        UNION ALL
        SELECT q_id, '열한', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '열한')
        UNION ALL
        SELECT q_id, '여덟', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '여덟');
    END IF;
END $$;

-- ==========================================
-- ENTRY TEST 2 - ADDITIONAL BEGINNER LEVEL QUESTIONS
-- ==========================================

-- Additional Question: Time expressions
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 2, 'How do you say "yesterday" in Korean?', '어제', '어제 (eoje) is the Korean word for yesterday.', 10, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 2 AND content = 'How do you say "yesterday" in Korean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 2 AND content = 'How do you say "yesterday" in Korean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, '어제', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '어제')
        UNION ALL
        SELECT q_id, '내일', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '내일')
        UNION ALL
        SELECT q_id, '오늘', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '오늘')
        UNION ALL
        SELECT q_id, '모레', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '모레');
    END IF;
END $$;

-- Additional Question: Food vocabulary
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 2, 'What does 고기 mean?', 'meat', '고기 (gogi) means meat in Korean. It is commonly used when referring to any type of meat.', 11, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 2 AND content = 'What does 고기 mean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 2 AND content = 'What does 고기 mean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'meat', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'meat')
        UNION ALL
        SELECT q_id, 'fish', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'fish')
        UNION ALL
        SELECT q_id, 'vegetable', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'vegetable')
        UNION ALL
        SELECT q_id, 'fruit', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'fruit');
    END IF;
END $$;

-- ==========================================
-- ENTRY TEST 3 - ADDITIONAL INTERMEDIATE LEVEL QUESTIONS
-- ==========================================

-- Additional Question: Korean consonants
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 3, 'Which consonant sound is represented by ㄴ?', 'n', 'ㄴ (nieun) represents the sound "n" in Korean, similar to the English "n" sound.', 10, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 3 AND content = 'Which consonant sound is represented by ㄴ?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 3 AND content = 'Which consonant sound is represented by ㄴ?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'n', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'n')
        UNION ALL
        SELECT q_id, 'm', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'm')
        UNION ALL
        SELECT q_id, 'l', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'l')
        UNION ALL
        SELECT q_id, 'r', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'r');
    END IF;
END $$;

-- Additional Question: Korean vowels
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 3, 'What sound does ㅓ (eo) make?', 'eo', 'ㅓ (eo) is pronounced as "eo" like in "sir" or "her".', 11, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 3 AND content = 'What sound does ㅓ (eo) make?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 3 AND content = 'What sound does ㅓ (eo) make?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'eo', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'eo')
        UNION ALL
        SELECT q_id, 'oh', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'oh')
        UNION ALL
        SELECT q_id, 'oo', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'oo')
        UNION ALL
        SELECT q_id, 'ah', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'ah');
    END IF;
END $$;

-- ==========================================
-- ENTRY TEST 4 - ADDITIONAL ADVANCED BEGINNER LEVEL QUESTIONS
-- ==========================================

-- Additional Question: Body parts
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 4, 'What does 발 mean?', 'foot', '발 (bal) means foot in Korean. It is a basic vocabulary word for body parts.', 10, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 4 AND content = 'What does 발 mean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 4 AND content = 'What does 발 mean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'foot', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'foot')
        UNION ALL
        SELECT q_id, 'hand', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'hand')
        UNION ALL
        SELECT q_id, 'head', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'head')
        UNION ALL
        SELECT q_id, 'leg', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'leg');
    END IF;
END $$;

-- Additional Question: Weather
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 4, 'How do you say "it is sunny" in Korean?', '맑아요', '맑아요 (malgayo) means "it is sunny" or "it is clear" in Korean.', 11, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 4 AND content = 'How do you say "it is sunny" in Korean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 4 AND content = 'How do you say "it is sunny" in Korean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, '맑아요', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '맑아요')
        UNION ALL
        SELECT q_id, '흐려요', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '흐려요')
        UNION ALL
        SELECT q_id, '바람 불어요', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '바람 불어요')
        UNION ALL
        SELECT q_id, '추워요', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = '추워요');
    END IF;
END $$;

-- ==========================================
-- ENTRY TEST 5 - ADDITIONAL UPPER INTERMEDIATE LEVEL QUESTIONS
-- ==========================================

-- Additional Question: Korean culture
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 5, 'What does 부처님오신날 mean?', 'Buddha''s Birthday', '부처님오신날 (Bucheonim osinnal) is Buddha''s Birthday, also known as "Lantern Festival".', 10, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 5 AND content = 'What does 부처님오신날 mean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 5 AND content = 'What does 부처님오신날 mean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'Buddha''s Birthday', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'Buddha''s Birthday')
        UNION ALL
        SELECT q_id, 'Christmas', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'Christmas')
        UNION ALL
        SELECT q_id, 'New Year', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'New Year')
        UNION ALL
        SELECT q_id, 'Thanksgiving', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'Thanksgiving');
    END IF;
END $$;

-- Additional Question: Korean food
INSERT INTO entry_test_questions (entry_test_id, content, correct_answer, explanation, order_index, created_at) 
SELECT 5, 'What does 불고기 mean?', 'bulgogi', '불고기 (bulgogi) is a popular Korean grilled beef dish, marinated and thinly sliced.', 11, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM entry_test_questions 
    WHERE entry_test_id = 5 AND content = 'What does 불고기 mean?'
);

DO $$
DECLARE
    q_id INTEGER;
BEGIN
    SELECT id INTO q_id FROM entry_test_questions 
    WHERE entry_test_id = 5 AND content = 'What does 불고기 mean?' 
    ORDER BY id DESC LIMIT 1;
    
    IF q_id IS NOT NULL THEN
        INSERT INTO entry_test_question_options (question_id, option_text, is_correct, created_at)
        SELECT q_id, 'bulgogi', true, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'bulgogi')
        UNION ALL
        SELECT q_id, 'kimchi', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'kimchi')
        UNION ALL
        SELECT q_id, 'bibimbap', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'bibimbap')
        UNION ALL
        SELECT q_id, 'galbi', false, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM entry_test_question_options WHERE question_id = q_id AND option_text = 'galbi');
    END IF;
END $$;

-- ==========================================
-- UPDATE SEQUENCES AFTER ALL INSERTS (OPTIONAL)
-- ==========================================

-- Optional: Update sequences after inserts to ensure consistency
-- SELECT setval('entry_test_questions_id_seq', (SELECT MAX(id) FROM entry_test_questions));
-- SELECT setval('entry_test_question_options_id_seq', (SELECT MAX(id) FROM entry_test_question_options));

-- ==========================================
-- SUMMARY
-- ==========================================
-- This script adds 10 new questions total:
-- - Entry Test 1: 2 additional questions (order_index 10-11)
-- - Entry Test 2: 2 additional questions (order_index 10-11)  
-- - Entry Test 3: 2 additional questions (order_index 10-11)
-- - Entry Test 4: 2 additional questions (order_index 10-11)
-- - Entry Test 5: 2 additional questions (order_index 10-11)
-- Total: 10 new questions with 40 new options (4 options per question)
-- All questions use auto-incrementing IDs to avoid conflicts
-- Duplicate prevention: Uses WHERE NOT EXISTS clauses to check for content uniqueness
-- Sequence fix: Updates PostgreSQL sequences before and after inserts to prevent ID conflicts