-- Dummy data for exercises table in Korean Learning App
-- This SQL script creates sample exercises for lessons 1-5
-- Just copy and paste into PostgreSQL

-- First, let's assume you have lessons with IDs 1-5
-- If not, you can adjust the lesson_id values below

-- Exercise types: listening, speaking, writing, pronunciation

-- Listening exercises (Lesson 1)
INSERT INTO exercises (lesson_id, type, title, content, audio_url, transcript, order_index, created_at)
VALUES
(1, 'listening', 'Listen to Basic Greetings', 'Listen to the audio and identify the greeting', 'https://storage.example.com/audio/basic_greetings_1.mp3', '안녕하세요 - Hello\n고맙습니다 - Thank you\n미안합니다 - Sorry', 1, NOW()),
(1, 'listening', 'Listen to Numbers', 'Listen and practice numbers 1-10', 'https://storage.example.com/audio/numbers_1_10.mp3', '하나 (hana) - 1\n둘 (dul) - 2\n셋 (set) - 3\n넷 (net) - 4\n다섯 (daseot) - 5', 2, NOW()),

-- Speaking exercises (Lesson 1)
(1, 'speaking', 'Practice Introductions', 'Practice introducing yourself', NULL, NULL, 'Introduce yourself in Korean: 안녕하세요, 저는 [Your Name]입니다.', '안녕하세요, 저는 길동입니다.\nHello, my name is Gildong.', 3, NOW()),
(1, 'speaking', 'Practice Greetings', 'Practice common greetings', NULL, NULL, 'Say these greetings: 안녕하세요, 안녕히가세요, 감사합니다', '안녕하세요 - Good morning/hello\n안녕히가세요 - Goodbye\n감사합니다 - Thank you', 4, NOW()),

-- Writing exercises (Lesson 1)
(1, 'writing', 'Write Basic Sentences', 'Practice writing simple sentences', NULL, NULL, 'Write: "I am a student"', '저는 학생입니다. (I am a student)', 5, NOW()),
(1, 'writing', 'Write Numbers', 'Practice writing Korean numbers', NULL, NULL, 'Write numbers 1-5 in Korean', '하나, 둘, 셋, 넷, 다섯', 6, NOW()),

-- Listening exercises (Lesson 2)
(2, 'listening', 'Listen to Family Terms', 'Learn family member terms', 'https://storage.example.com/audio/family_terms.mp3', '아버지 - Father\n어머니 - Mother\n형/누나 - Older brother/sister', 1, NOW()),
(2, 'listening', 'Listen to Food Names', 'Learn basic food vocabulary', 'https://storage.example.com/audio/food_names.mp3', '밥 - Rice\n고기 - Meat\n물 - Water\n채소 - Vegetables', 2, NOW()),

-- Speaking exercises (Lesson 2)
(2, 'speaking', 'Talk About Family', 'Describe your family', NULL, NULL, 'Describe your family members', '우리 가족은 모두 네 명입니다.\nOur family has four members.', 3, NOW()),
(2, 'speaking', 'Order Food', 'Practice ordering food', NULL, NULL, 'Practice: "I would like some rice"', '밥 좀 주세요. (Please give me some rice)', 4, NOW()),

-- Writing exercises (Lesson 2)
(2, 'writing', 'Write Family Introduction', 'Write about your family', NULL, NULL, 'Write about your family using learned terms', '우리 아버지는 선생님입니다.\nOur father is a teacher.', 5, NOW()),
(2, 'writing', 'Write Shopping List', 'Practice writing a simple shopping list', NULL, NULL, 'Write a shopping list with 5 items', '고기, 물, 채소, 빵, 과일', 6, NOW()),

-- Listening exercises (Lesson 3)
(3, 'listening', 'Listen to Time Expressions', 'Learn to tell time', 'https://storage.example.com/audio/time_expressions.mp3', '지금 - Now\n오늘 - Today\n내일 - Tomorrow\n어제 - Yesterday', 1, NOW()),
(3, 'listening', 'Listen to Daily Routines', 'Learn daily routine vocabulary', 'https://storage.example.com/audio/daily_routines.mp3', '일어나다 - Wake up\n먹다 - Eat\n자다 - Sleep\n공부하다 - Study', 2, NOW()),

-- Speaking exercises (Lesson 3)
(3, 'speaking', 'Describe Your Daily Routine', 'Talk about your daily schedule', NULL, NULL, 'Describe your typical day', '저는 아침 7시에 일어나고, 8시에 밥을 먹습니다.\nI wake up at 7 and eat at 8.', 3, NOW()),
(3, 'speaking', 'Make Appointments', 'Practice scheduling', NULL, NULL, 'Practice: "When can we meet?"', '언제 만날 수 있나요? (When can we meet?)', 4, NOW()),

-- Writing exercises (Lesson 3)
(3, 'writing', 'Write Your Schedule', 'Write your daily schedule', NULL, NULL, 'Write your daily schedule from morning to night', '아침 7시 - 일어나기\n8시 - 아침 식사\n9시 - 공부 시작', 5, NOW()),
(3, 'writing', 'Write About Yesterday', 'Practice past tense', NULL, NULL, 'Write about what you did yesterday', '어제 도서관에 갔습니다.\nYesterday I went to the library.', 6, NOW()),

-- Listening exercises (Lesson 4)
(4, 'listening', 'Listen to Directions', 'Learn location and direction words', 'https://storage.example.com/audio/directions.mp3', '오른쪽 - Right\n왼쪽 - Left\n앞 - Front\n뒤 - Back', 1, NOW()),
(4, 'listening', 'Listen to Transportation', 'Learn transportation vocabulary', 'https://storage.example.com/audio/transportation.mp3', '버스 - Bus\n지하철 - Subway\n택시 - Taxi\n비행기 - Airplane', 2, NOW()),

-- Speaking exercises (Lesson 4)
(4, 'speaking', 'Give Directions', 'Practice giving directions', NULL, NULL, 'Give directions to the nearest subway station', '지하철역은 오른쪽으로 가세요.\nGo right to the subway station.', 3, NOW()),
(4, 'speaking', 'Ask for Directions', 'Practice asking for help', NULL, NULL, 'Practice: "How do I get to...?"', '지하철역이 어디에 있나요? (Where is the subway station?)', 4, NOW()),

-- Writing exercises (Lesson 4)
(4, 'writing', 'Write Directions', 'Write step-by-step directions', NULL, NULL, 'Write how to get from school to your home', '학교에서 나와서 오른쪽으로 가십시오...', 5, NOW()),
(4, 'writing', 'Describe Transportation', 'Write about your transportation', NULL, NULL, 'Write about how you commute', '저는 지하철로 출근합니다.\nI commute by subway.', 6, NOW()),

-- Listening exercises (Lesson 5)
(5, 'listening', 'Listen to Weather', 'Learn weather vocabulary', 'https://storage.example.com/audio/weather.mp3', '날씨 - Weather\n비 - Rain\n눈 - Snow\n맑음 - Sunny', 1, NOW()),
(5, 'listening', 'Listen to Clothing', 'Learn clothing vocabulary', 'https://storage.example.com/audio/clothing.mp3', '옷 - Clothes\n바지 - Pants\n셔츠 - Shirt\n신발 - Shoes', 2, NOW()),

-- Speaking exercises (Lesson 5)
(5, 'speaking', 'Talk About Weather', 'Describe the weather', NULL, NULL, 'Describe today'\''s weather', '오늘 날씨가 맑습니다.\nToday the weather is sunny.', 3, NOW()),
(5, 'speaking', 'Shop for Clothes', 'Practice shopping conversation', NULL, NULL, 'Practice shopping for clothes', '이 셔츠는 얼마입니까? (How much is this shirt?)', 4, NOW()),

-- Writing exercises (Lesson 5)
(5, 'writing', 'Write Weather Report', 'Write a simple weather report', NULL, NULL, 'Write a weekend weather forecast', '주말 날씨는 맑고 따뜻할 것입니다.\nThe weekend weather will be sunny and warm.', 5, NOW()),
(5, 'writing', 'Describe Your Outfit', 'Write about what you are wearing', NULL, NULL, 'Describe your current outfit', '저는 파란 셔츠와 검은 바지를 입고 있습니다.\nI am wearing a blue shirt and black pants.', 6, NOW());

-- Pronunciation exercises (scattered across lessons)
INSERT INTO exercises (lesson_id, type, title, content, audio_url, transcript, prompt, sample_answer, order_index, created_at)
VALUES
(1, 'pronunciation', 'Practice Vowel Sounds', 'Practice basic vowel pronunciation', 'https://storage.example.com/audio/vowels.mp3', 'ㅏ (a) - like "ah"\nㅓ (eo) - like "uh"\nㅗ (o) - like "oh"\nㅜ (u) - like "oo"', 'Repeat each vowel after the audio', 'Pay attention to mouth shape and tongue position', 7, NOW()),
(2, 'pronunciation', 'Practice Consonants', 'Practice basic consonants', 'https://storage.example.com/audio/consonants.mp3', 'ㄱ (g/k) - soft G sound\nㄴ (n) - N sound\nㅁ (m) - M sound', 'Repeat each consonant clearly', 'Start softly, end with a stop', 7, NOW()),
(3, 'pronunciation', 'Practice Syllable Blocks', 'Practice reading syllable blocks', 'https://storage.example.com/audio/syllables.mp3', '가 나 다 라 마 바 사\n하나 둘 셋 넷 다섯', 'Practice reading these syllables', 'Remember: top-left-right-bottom order', 7, NOW()),
(4, 'pronunciation', 'Practice Tone and Stress', 'Learn Korean stress patterns', 'https://storage.example.com/audio/tone_patterns.mp3', '안녕하세요 - stress on 녕\n고맙습니다 - stress on 맙', 'Practice with proper stress', 'Korean does not have tone, but has stress', 7, NOW()),
(5, 'pronunciation', 'Practice Speech Flow', 'Practice natural speech rhythm', 'https://storage.example.com/audio/speech_flow.mp3', 'Practice natural pause and rhythm', 'Read sentences naturally', 'Focus on smooth transitions between words', 7, NOW());

-- Verification query (optional)
-- SELECT * FROM exercises ORDER BY lesson_id, order_index;

