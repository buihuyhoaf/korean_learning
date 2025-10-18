-- ============================================
-- QUIZ DUMMY DATA FOR KOREAN LEARNING APP
-- This script creates realistic quiz data with questions and options
-- ============================================

BEGIN;

-- ============================================
-- 1. QUESTION TYPES (Prerequisites)
-- ============================================

INSERT INTO question_types (id, name, description) VALUES
(1, 'Multiple Choice', 'Select the correct answer from given options'),
(2, 'Fill in the Blank', 'Complete the sentence with the appropriate word or phrase'),
(3, 'True/False', 'Determine whether the statement is correct or incorrect'),
(4, 'Audio Comprehension', 'Listen to audio and answer questions about the content'),
(5, 'Writing Practice', 'Compose sentences or short texts based on prompts'),
(6, 'Reading Comprehension', 'Read passages and answer questions about the content'),
(7, 'Matching', 'Match Korean words with their English translations or definitions'),
(8, 'Pronunciation', 'Practice and verify correct Korean pronunciation')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 2. ENSURING PREREQUISITE DATA EXISTS
-- ============================================

-- Ensure we have courses
INSERT INTO courses (id, title, description, order_index, created_at) VALUES
(1, 'Korean Fundamentals', 'Complete beginner course covering Hangul basics, essential vocabulary, and fundamental grammar.', 1, NOW() - INTERVAL '45 days'),
(2, 'Korean Intermediate', 'Intermediate course focusing on complex grammar patterns, conversational skills, and cultural context.', 2, NOW() - INTERVAL '40 days'),
(3, 'Korean Advanced', 'Advanced course for fluent communication, business Korean, and understanding of nuanced cultural expressions.', 3, NOW() - INTERVAL '35 days')
ON CONFLICT (id) DO NOTHING;

-- Ensure we have units
INSERT INTO units (id, course_id, title, description, order_index, created_at) VALUES
(1, 1, 'Hangul Mastery', 'Master the Korean alphabet system with proper pronunciation and writing practice.', 1, NOW() - INTERVAL '44 days'),
(2, 1, 'Essential Vocabulary', 'Learn fundamental words for daily conversation and basic communication.', 2, NOW() - INTERVAL '43 days'),
(3, 2, 'Complex Grammar Patterns', 'Master advanced sentence structures and nuanced grammatical expressions.', 1, NOW() - INTERVAL '39 days'),
(4, 3, 'Business Korean', 'Specialized vocabulary and expressions for workplace communication.', 1, NOW() - INTERVAL '29 days')
ON CONFLICT (id) DO NOTHING;

-- Ensure we have lessons
INSERT INTO lessons (id, unit_id, title, description, order_index, created_at) VALUES
(1, 1, 'Introduction to Hangul', 'Learn about the history and structure of the Korean alphabet system.', 1, NOW() - INTERVAL '44 days'),
(2, 1, 'Basic Consonants', 'Master the 14 basic consonants with proper pronunciation exercises.', 2, NOW() - INTERVAL '43 days'),
(3, 2, 'Numbers & Counting', 'Learn Korean numbers, counters, and how to count different objects.', 1, NOW() - INTERVAL '43 days'),
(4, 2, 'Family & Relationships', 'Essential vocabulary for family members and social relationships.', 2, NOW() - INTERVAL '42 days'),
(5, 3, 'Honorifics System', 'Understanding and using Korean honorific language appropriately.', 1, NOW() - INTERVAL '38 days'),
(6, 3, 'Conditional Statements', 'Master if-then structures and hypothetical situations in Korean.', 2, NOW() - INTERVAL '37 days'),
(7, 4, 'Business Etiquette', 'Understand Korean business culture and appropriate workplace behavior.', 1, NOW() - INTERVAL '29 days'),
(8, 4, 'Meeting Vocabulary', 'Master vocabulary for business meetings and professional presentations.', 2, NOW() - INTERVAL '28 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 3. QUIZZES (Korean Learning Quizzes)
-- ============================================

INSERT INTO quizzes (id, lesson_id, title, description, type, order_index, created_at) VALUES
-- Hangul Introduction Quiz
(1, 1, 'Hangul Fundamentals Quiz', 'Test your knowledge of basic Hangul characters and pronunciation rules.', 'vocabulary', 1, NOW() - INTERVAL '44 days'),
(2, 1, 'Hangul Recognition Practice', 'Practice recognizing and writing basic Hangul characters.', 'vocabulary', 2, NOW() - INTERVAL '44 days'),

-- Basic Consonants Quiz
(3, 2, 'Consonants Mastery Test', 'Test your understanding of Korean basic consonants (자음).', 'vocabulary', 1, NOW() - INTERVAL '43 days'),
(4, 2, 'Consonant Pronunciation', 'Practice pronunciation of Korean consonants with audio support.', 'listening', 2, NOW() - INTERVAL '43 days'),

-- Numbers & Counting Quiz
(5, 3, 'Korean Numbers Quiz', 'Test your knowledge of Korean numbers and counting systems.', 'vocabulary', 1, NOW() - INTERVAL '43 days'),
(6, 3, 'Number Usage Practice', 'Practice using numbers in different contexts and situations.', 'writing', 2, NOW() - INTERVAL '43 days'),

-- Family & Relationships Quiz
(7, 4, 'Family Vocabulary Test', 'Test your knowledge of Korean family relationship terms.', 'vocabulary', 1, NOW() - INTERVAL '42 days'),
(8, 4, 'Relationship Reading', 'Read passages about Korean families and answer comprehension questions.', 'reading', 2, NOW() - INTERVAL '42 days'),

-- Honorifics System Quiz
(9, 5, 'Honorifics Assessment', 'Test your understanding of Korean honorific language and usage.', 'vocabulary', 1, NOW() - INTERVAL '38 days'),
(10, 5, 'Formal vs Informal Quiz', 'Practice distinguishing between formal and informal Korean expressions.', 'vocabulary', 2, NOW() - INTERVAL '38 days'),

-- Conditional Statements Quiz
(11, 6, 'Conditional Grammar Test', 'Test your knowledge of Korean conditional sentence structures.', 'vocabulary', 1, NOW() - INTERVAL '37 days'),
(12, 6, 'Hypothetical Situations', 'Practice creating conditional sentences in Korean.', 'writing', 2, NOW() - INTERVAL '37 days'),

-- Business Etiquette Quiz
(13, 7, 'Business Culture Quiz', 'Test your knowledge of Korean business etiquette and cultural norms.', 'vocabulary', 1, NOW() - INTERVAL '29 days'),
(14, 7, 'Workplace Communication', 'Practice appropriate business communication in Korean context.', 'speaking', 2, NOW() - INTERVAL '29 days'),

-- Meeting Vocabulary Quiz
(15, 8, 'Meeting Terms Test', 'Test your knowledge of business meeting vocabulary and expressions.', 'vocabulary', 1, NOW() - INTERVAL '28 days'),
(16, 8, 'Presentation Skills', 'Practice vocabulary and phrases for giving presentations in Korean.', 'speaking', 2, NOW() - INTERVAL '28 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 4. QUESTIONS (Realistic Korean Questions)
-- ============================================

INSERT INTO questions (id, quiz_id, question_type_id, content, audio_url, image_url, correct_answer, explanation, order_index, created_at) VALUES
-- Quiz 1: Hangul Fundamentals (5 questions)
(1, 1, 1, '한글은 몇 개의 기본 자음으로 이루어져 있나요?', NULL, NULL, '14', '한글은 14개의 기본 자음(ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅅ, ㅇ, ㅈ, ㅊ, ㅋ, ㅌ, ㅍ, ㅎ)으로 이루어져 있습니다.', 1, NOW() - INTERVAL '44 days'),
(2, 1, 1, '한글을 만든 왕은 누구인가요?', NULL, NULL, '세종대왕', '세종대왕(1418-1450)이 한글을 만들었습니다. 1443년 훈민정음을 창제했습니다.', 2, NOW() - INTERVAL '44 days'),
(3, 1, 3, '한글은 동아시아에서 유일하게 한자에 기반하지 않은 문자입니다.', NULL, NULL, 'True', '맞습니다. 한글은 창제된 문자로, 한자나 다른 문자에 기반하지 않고 독립적으로 만들어졌습니다.', 3, NOW() - INTERVAL '44 days'),
(4, 1, 2, '한글의 기본 모음은 ___개입니다.', NULL, NULL, '10', '한글의 기본 모음은 10개입니다: ㅏ, ㅑ, ㅓ, ㅕ, ㅗ, ㅛ, ㅜ, ㅠ, ㅡ, ㅣ', 4, NOW() - INTERVAL '44 days'),
(5, 1, 1, '한글의 특징으로 올바른 것은?', NULL, NULL, '음소문자', '한글은 음소문자로, 각 글자가 하나의 음소를 나타냅니다.', 5, NOW() - INTERVAL '44 days'),

-- Quiz 3: Consonants Mastery (5 questions)
(6, 3, 1, '"ㄱ"의 발음은 무엇인가요?', 'https://example.com/audio/gieuk.mp3', NULL, 'g/k', 'ㄱ은 [g] 또는 [k] 소리로 발음됩니다. 초성에서는 [k], 종성에서는 [g]로 발음됩니다.', 1, NOW() - INTERVAL '43 days'),
(7, 3, 4, '다음 중 가장 강한 기식음은?', 'https://example.com/audio/aspirated_consonants.mp3', NULL, 'ㅋ', 'ㅋ은 ㄱ의 강한 기식음으로, 더 강한 기식과 함께 발음됩니다.', 2, NOW() - INTERVAL '43 days'),
(8, 3, 1, '"ㄴ"의 영어 대응음은?', NULL, NULL, 'n', 'ㄴ은 영어의 [n] 소리와 같습니다.', 3, NOW() - INTERVAL '43 days'),
(9, 3, 3, '"ㄹ"은 항상 [l] 소리로 발음됩니다.', NULL, NULL, 'False', 'ㄹ은 위치에 따라 [l] 또는 [r] 소리로 발음됩니다. 초성에서는 [r], 종성에서는 [l]에 가깝습니다.', 4, NOW() - INTERVAL '43 days'),
(10, 3, 1, '다음 중 유성음이 아닌 자음은?', NULL, NULL, 'ㅌ', 'ㅌ은 무성음이고, ㄴ, ㅁ, ㄹ은 유성음입니다.', 5, NOW() - INTERVAL '43 days'),

-- Quiz 5: Korean Numbers (6 questions)
(11, 5, 1, '한국어 숫자 "일"은 영어로 무엇인가요?', NULL, NULL, '1', '일은 한국어에서 1을 의미합니다.', 1, NOW() - INTERVAL '43 days'),
(12, 5, 1, '사과 3개를 세는 올바른 표현은?', NULL, NULL, '사과 세 개', '사과는 개 단위로 셀 때 "세 개"라고 합니다.', 2, NOW() - INTERVAL '43 days'),
(13, 5, 1, '한국어에서 시간을 말할 때 사용하는 숫자는?', NULL, NULL, '한국어 숫자', '시간을 말할 때는 한국어 숫자(하나, 둘, 셋...)를 사용합니다.', 3, NOW() - INTERVAL '43 days'),
(14, 5, 2, '사람 수를 셀 때 "___명"을 사용합니다.', NULL, NULL, '스무', '사람 20명은 "스무 명"이라고 합니다.', 4, NOW() - INTERVAL '43 days'),
(15, 5, 1, '다음 중 올바른 숫자 배열은?', NULL, NULL, '하나, 둘, 셋', '한국어 숫자 순서는 하나, 둘, 셋... 입니다.', 5, NOW() - INTERVAL '43 days'),
(16, 5, 3, '한국어에는 두 가지 숫자 체계가 있습니다.', NULL, NULL, 'True', '맞습니다. 한국어에는 한자어 숫자(일, 이, 삼...)와 한국어 숫자(하나, 둘, 셋...)가 있습니다.', 6, NOW() - INTERVAL '43 days'),

-- Quiz 7: Family Vocabulary (5 questions)
(17, 7, 1, '"아버지"의 의미는?', NULL, 'https://example.com/images/father.jpg', 'Father', '아버지는 아버지, 부친을 의미합니다.', 1, NOW() - INTERVAL '42 days'),
(18, 7, 1, '여동생을 한국어로?', NULL, NULL, '여동생', '여동생은 누나보다 어린 여자 형제를 의미합니다.', 2, NOW() - INTERVAL '42 days'),
(19, 7, 1, '"할머니"는 어떤 관계인가요?', NULL, NULL, 'Grandmother', '할머니는 할머니, 조모를 의미합니다.', 3, NOW() - INTERVAL '42 days'),
(20, 7, 2, '형보다 나이가 많은 남자 형제는 "___형"이라고 합니다.', NULL, NULL, '큰', '큰형은 형보다 나이가 많은 남자 형제를 의미합니다.', 4, NOW() - INTERVAL '42 days'),
(21, 7, 1, '다음 중 올바른 가족 관계는?', NULL, NULL, '아빠와 아들', '아빠와 아들은 부자 관계입니다.', 5, NOW() - INTERVAL '42 days'),

-- Quiz 9: Honorifics Assessment (6 questions)
(22, 9, 1, '한국어에서 존댓말을 사용하는 이유는?', NULL, NULL, '상대방에 대한 존중', '한국어에서 존댓말은 상대방에 대한 존중과 배려를 표현합니다.', 1, NOW() - INTERVAL '38 days'),
(23, 9, 1, '"드시다"는 어떤 동사의 존댓말인가요?', NULL, NULL, '먹다', '드시다는 먹다의 존댓말입니다.', 2, NOW() - INTERVAL '38 days'),
(24, 9, 3, '나이가 같으면 항상 반말을 사용해야 합니다.', NULL, NULL, 'False', '나이가 같아도 처음 만나는 사람에게는 존댓말을 사용하는 것이 예의입니다.', 3, NOW() - INTERVAL '38 days'),
(25, 9, 1, '다음 중 가장 정중한 인사말은?', NULL, NULL, '안녕하세요', '안녕하세요가 가장 정중하고 일반적인 인사말입니다.', 4, NOW() - INTERVAL '38 days'),
(26, 9, 2, '존댓말에서 "가시다"는 "___"의 높임 표현입니다.', NULL, NULL, '가다', '가시다는 가다의 존댓말입니다.', 5, NOW() - INTERVAL '38 days'),
(27, 9, 1, '한국어 존댓말의 특징으로 올바른 것은?', NULL, NULL, '사회적 관계를 반영', '한국어 존댓말은 사회적 관계와 계층을 반영합니다.', 6, NOW() - INTERVAL '38 days'),

-- Quiz 13: Business Culture (5 questions)
(28, 13, 1, '한국 비즈니스에서 명함을 받을 때 어떻게 해야 하나요?', NULL, NULL, '두 손으로 받기', '명함을 받을 때는 두 손으로 정중하게 받아야 합니다.', 1, NOW() - INTERVAL '29 days'),
(29, 13, 1, '한국 비즈니스 미팅에서 가장 중요한 것은?', NULL, NULL, '관계 구축', '한국 비즈니스에서는 신뢰와 관계 구축이 매우 중요합니다.', 2, NOW() - INTERVAL '29 days'),
(30, 13, 3, '한국에서 비즈니스 미팅은 항상 정시에 시작됩니다.', NULL, NULL, 'False', '한국 비즈니스에서는 관계를 중시하므로 시간보다는 관계 구축이 우선될 수 있습니다.', 3, NOW() - INTERVAL '29 days'),
(31, 13, 1, '한국 비즈니스에서 적절한 좌석은?', NULL, NULL, '상대방과 마주보는 자리', '비즈니스 미팅에서는 상대방과 마주보는 자리를 선택합니다.', 4, NOW() - INTERVAL '29 days'),
(32, 13, 2, '한국 비즈니스에서 "___"을/를 먼저 나누는 것이 일반적입니다.', NULL, NULL, '인사', '한국 비즈니스에서는 먼저 정중한 인사를 나누는 것이 중요합니다.', 5, NOW() - INTERVAL '29 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 5. QUESTION OPTIONS (Multiple Choice Options)
-- ============================================

INSERT INTO question_options (id, question_id, option_text, is_correct, created_at) VALUES
-- Question 1: Hangul basic consonants
(1, 1, '14', true, NOW() - INTERVAL '44 days'),
(2, 1, '10', false, NOW() - INTERVAL '44 days'),
(3, 1, '19', false, NOW() - INTERVAL '44 days'),
(4, 1, '21', false, NOW() - INTERVAL '44 days'),

-- Question 2: King who created Hangul
(5, 2, '세종대왕', true, NOW() - INTERVAL '44 days'),
(6, 2, '이성계', false, NOW() - INTERVAL '44 days'),
(7, 2, '정조', false, NOW() - INTERVAL '44 days'),
(8, 2, '고종', false, NOW() - INTERVAL '44 days'),

-- Question 5: Hangul characteristics
(9, 5, '음소문자', true, NOW() - INTERVAL '44 days'),
(10, 5, '표의문자', false, NOW() - INTERVAL '44 days'),
(11, 5, '음절문자', false, NOW() - INTERVAL '44 days'),
(12, 5, '상형문자', false, NOW() - INTERVAL '44 days'),

-- Question 6: Consonant ㄱ pronunciation
(13, 6, 'g/k', true, NOW() - INTERVAL '43 days'),
(14, 6, 'j/ch', false, NOW() - INTERVAL '43 days'),
(15, 6, 't/d', false, NOW() - INTERVAL '43 days'),
(16, 6, 'p/b', false, NOW() - INTERVAL '43 days'),

-- Question 7: Strongest aspirated sound
(17, 7, 'ㅋ', true, NOW() - INTERVAL '43 days'),
(18, 7, 'ㅌ', false, NOW() - INTERVAL '43 days'),
(19, 7, 'ㅍ', false, NOW() - INTERVAL '43 days'),
(20, 7, 'ㅊ', false, NOW() - INTERVAL '43 days'),

-- Question 8: ㄴ English equivalent
(21, 8, 'n', true, NOW() - INTERVAL '43 days'),
(22, 8, 'm', false, NOW() - INTERVAL '43 days'),
(23, 8, 'l', false, NOW() - INTERVAL '43 days'),
(24, 8, 'r', false, NOW() - INTERVAL '43 days'),

-- Question 10: Voiceless consonant
(25, 10, 'ㅌ', true, NOW() - INTERVAL '43 days'),
(26, 10, 'ㄴ', false, NOW() - INTERVAL '43 days'),
(27, 10, 'ㅁ', false, NOW() - INTERVAL '43 days'),
(28, 10, 'ㄹ', false, NOW() - INTERVAL '43 days'),

-- Question 11: Korean number 일
(29, 11, '1', true, NOW() - INTERVAL '43 days'),
(30, 11, '2', false, NOW() - INTERVAL '43 days'),
(31, 11, '10', false, NOW() - INTERVAL '43 days'),
(32, 11, '100', false, NOW() - INTERVAL '43 days'),

-- Question 12: Counting apples
(33, 12, '사과 세 개', true, NOW() - INTERVAL '43 days'),
(34, 12, '사과 셋 개', false, NOW() - INTERVAL '43 days'),
(35, 12, '사과 삼 개', false, NOW() - INTERVAL '43 days'),
(36, 12, '사과 서 개', false, NOW() - INTERVAL '43 days'),

-- Question 13: Time counting numbers
(37, 13, '한국어 숫자', true, NOW() - INTERVAL '43 days'),
(38, 13, '한자어 숫자', false, NOW() - INTERVAL '43 days'),
(39, 13, '영어 숫자', false, NOW() - INTERVAL '43 days'),
(40, 13, '일본어 숫자', false, NOW() - INTERVAL '43 days'),

-- Question 15: Correct number sequence
(41, 15, '하나, 둘, 셋', true, NOW() - INTERVAL '43 days'),
(42, 15, '일, 이, 삼', false, NOW() - INTERVAL '43 days'),
(43, 15, 'first, second, third', false, NOW() - INTERVAL '43 days'),
(44, 15, '하나, 이, 셋', false, NOW() - INTERVAL '43 days'),

-- Question 17: 아버지 meaning
(45, 17, 'Father', true, NOW() - INTERVAL '42 days'),
(46, 17, 'Mother', false, NOW() - INTERVAL '42 days'),
(47, 17, 'Brother', false, NOW() - INTERVAL '42 days'),
(48, 17, 'Grandfather', false, NOW() - INTERVAL '42 days'),

-- Question 18: Younger sister
(49, 18, '여동생', true, NOW() - INTERVAL '42 days'),
(50, 18, '누나', false, NOW() - INTERVAL '42 days'),
(51, 18, '언니', false, NOW() - INTERVAL '42 days'),
(52, 18, '형', false, NOW() - INTERVAL '42 days'),

-- Question 19: 할머니
(53, 19, 'Grandmother', true, NOW() - INTERVAL '42 days'),
(54, 19, 'Mother', false, NOW() - INTERVAL '42 days'),
(55, 19, 'Aunt', false, NOW() - INTERVAL '42 days'),
(56, 19, 'Sister', false, NOW() - INTERVAL '42 days'),

-- Question 21: Correct family relationship
(57, 21, '아빠와 아들', true, NOW() - INTERVAL '42 days'),
(58, 21, '언니와 동생', false, NOW() - INTERVAL '42 days'),
(59, 21, '할아버지와 손자', false, NOW() - INTERVAL '42 days'),
(60, 21, '삼촌과 조카', false, NOW() - INTERVAL '42 days'),

-- Question 22: Why use honorifics
(61, 22, '상대방에 대한 존중', true, NOW() - INTERVAL '38 days'),
(62, 22, '문법적 규칙', false, NOW() - INTERVAL '38 days'),
(63, 22, '발음의 편의', false, NOW() - INTERVAL '38 days'),
(64, 22, '문장의 길이', false, NOW() - INTERVAL '38 days'),

-- Question 23: 드시다 meaning
(65, 23, '먹다', true, NOW() - INTERVAL '38 days'),
(66, 23, '마시다', false, NOW() - INTERVAL '38 days'),
(67, 23, '가다', false, NOW() - INTERVAL '38 days'),
(68, 23, '보다', false, NOW() - INTERVAL '38 days'),

-- Question 25: Most polite greeting
(69, 25, '안녕하세요', true, NOW() - INTERVAL '38 days'),
(70, 25, '안녕', false, NOW() - INTERVAL '38 days'),
(71, 25, '하이', false, NOW() - INTERVAL '38 days'),
(72, 25, '헬로', false, NOW() - INTERVAL '38 days'),

-- Question 27: Honorific characteristics
(73, 27, '사회적 관계를 반영', true, NOW() - INTERVAL '38 days'),
(74, 27, '발음만 바뀜', false, NOW() - INTERVAL '38 days'),
(75, 27, '의미가 바뀜', false, NOW() - INTERVAL '38 days'),
(76, 27, '문법만 다름', false, NOW() - INTERVAL '38 days'),

-- Question 28: Receiving business cards
(77, 28, '두 손으로 받기', true, NOW() - INTERVAL '29 days'),
(78, 28, '한 손으로 받기', false, NOW() - INTERVAL '29 days'),
(79, 28, '바로 주머니에 넣기', false, NOW() - INTERVAL '29 days'),
(80, 28, '뒤쪽에 서명하기', false, NOW() - INTERVAL '29 days'),

-- Question 29: Most important in business meetings
(81, 29, '관계 구축', true, NOW() - INTERVAL '29 days'),
(82, 29, '빠른 결정', false, NOW() - INTERVAL '29 days'),
(83, 29, '저렴한 가격', false, NOW() - INTERVAL '29 days'),
(84, 29, '정확한 시간', false, NOW() - INTERVAL '29 days'),

-- Question 31: Appropriate seating
(85, 31, '상대방과 마주보는 자리', true, NOW() - INTERVAL '29 days'),
(86, 31, '옆 자리', false, NOW() - INTERVAL '29 days'),
(87, 31, '뒤쪽 자리', false, NOW() - INTERVAL '29 days'),
(88, 31, '문 가까운 자리', false, NOW() - INTERVAL '29 days')
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

SELECT 'QUIZ DUMMY DATA VERIFICATION' as status;

-- Show counts
SELECT 'question_types' as table_name, COUNT(*) as row_count FROM question_types
UNION ALL
SELECT 'quizzes', COUNT(*) FROM quizzes
UNION ALL
SELECT 'questions', COUNT(*) FROM questions
UNION ALL
SELECT 'question_options', COUNT(*) FROM question_options
ORDER BY table_name;

-- Show sample data
SELECT 'SAMPLE QUIZZES' as info, id, title, type, lesson_id FROM quizzes ORDER BY id LIMIT 5;

SELECT 'SAMPLE QUESTIONS' as info, 
    q.title as quiz_title,
    qt.name as question_type,
    qu.content as question,
    qu.correct_answer
FROM questions qu
JOIN quizzes q ON qu.quiz_id = q.id
JOIN question_types qt ON qu.question_type_id = qt.id
ORDER BY qu.id LIMIT 5;

SELECT 'TOTAL QUESTIONS PER QUIZ' as info,
    q.title as quiz_title,
    COUNT(qu.id) as question_count
FROM quizzes q
LEFT JOIN questions qu ON q.id = qu.quiz_id
GROUP BY q.id, q.title
ORDER BY q.id;
