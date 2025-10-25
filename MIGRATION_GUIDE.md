# Database Migration Guide - Korean Learning App

## 🎯 Mục tiêu Migration

Chuyển đổi cấu trúc database từ:
```
Lesson → Quiz → Questions
```

Thành:
```
Lesson → Questions (practice questions)
Unit → Quiz (final unit test)
```

## 📋 Cấu trúc mới

```
📖 Korean for Beginners
├── 📚 Unit 1: Basic Greetings
│   ├── 📝 Lesson 1: 안녕하세요 (Hello)
│   │   ├── 🎯 Question: gồm nhiều question khác nhau (multiple-choice, listening, speaking, writing)
│   │   ├── 🎧 Listening Exercise: Greeting Dialogues
│   │   ├── 🎤 Speaking Exercise: Practice Greetings
│   │   └── ✍️ Writing Exercise: Write Greeting Sentences
│   └── 🧩 Final Quiz: kiểm tra cuối unit
```

## 🚀 Các bước thực hiện

### Step 1: Backup Database
```bash
# Backup trước khi migration
pg_dump your_database > backup_before_migration.sql
```

### Step 2: Chạy Migration Commands

```bash
# Tạo migration file
alembic revision -m "restructure_course_content_support_lesson_questions_and_unit_quizzes"

# Chạy migration
alembic upgrade head

# Kiểm tra migration
alembic current
alembic history
```

### Step 3: Verify Migration

```sql
-- Kiểm tra cấu trúc mới
SELECT * FROM lesson_content LIMIT 5;
SELECT * FROM unit_test_quizzes LIMIT 5;

-- Kiểm tra questions có lesson_id
SELECT COUNT(*) FROM questions WHERE lesson_id IS NOT NULL;

-- Kiểm tra quizzes có unit_id
SELECT COUNT(*) FROM quizzes WHERE unit_id IS NOT NULL;
```

## 📊 Thay đổi Database Schema

### Tables được modify:

#### 1. `questions` table
- **Thêm**: `lesson_id` (INTEGER, nullable) - Reference đến lesson
- **Thêm**: `question_type` (VARCHAR(50)) - Loại question: practice, assessment, listening, speaking, writing
- **Giữ**: `quiz_id` (INTEGER) - Vẫn giữ cho backward compatibility

#### 2. `quizzes` table  
- **Thêm**: `unit_id` (INTEGER, nullable) - Reference đến unit cho final quiz
- **Giữ**: `lesson_id` (INTEGER) - Vẫn giữ cho backward compatibility

### Views được tạo:

#### 1. `lesson_content` view
- Tổng hợp tất cả content của một lesson
- Bao gồm: practice questions, listening/speaking/writing exercises
- Dễ dàng query lesson content

#### 2. `unit_test_quizzes` view
- Hiển thị tất cả unit test quizzes
- Bao gồm thông tin unit và course
- Dễ dàng query unit tests

## 🔄 Data Migration Logic

### Questions Migration:
1. **Tất cả questions** từ existing quizzes được **copy** sang lesson
2. **Giữ nguyên** quiz_id để backward compatibility
3. **Thêm** lesson_id để support cấu trúc mới
4. **Set** question_type = 'practice'

### Quizzes Migration:
1. **Existing quizzes** được chuyển thành **unit tests**
2. **Thêm** unit_id = lesson.unit_id
3. **Update** type = 'unit_test'
4. **Giữ nguyên** lesson_id để backward compatibility

## ⚠️ Lưu ý quan trọng

### 1. Backward Compatibility
- **Không xóa** existing columns
- **Giữ nguyên** existing relationships
- **Existing APIs** vẫn hoạt động

### 2. Data Integrity
- **Foreign key constraints** được thêm
- **Indexes** được tạo cho performance
- **Data validation** được thêm

### 3. Rollback Plan
```bash
# Nếu cần rollback
alembic downgrade -1
```

## 🎯 API Changes Required

### New Endpoints cần tạo:
```python
# Get lesson questions (practice)
GET /v1/lessons/{lesson_id}/questions

# Get unit test quiz
GET /v1/units/{unit_id}/quiz

# Submit lesson question attempt
POST /v1/lessons/{lesson_id}/questions/{question_id}/attempt

# Submit unit test attempt  
POST /v1/units/{unit_id}/quiz/attempt
```

### Existing Endpoints vẫn hoạt động:
```python
# Vẫn hoạt động với quiz_id
GET /v1/quizzes/{quiz_id}
POST /v1/quizzes/{quiz_id}/attempt
```

## 📱 Android App Changes

### LessonScreenProgressive cần update:
1. **Load lesson questions** trực tiếp từ lesson
2. **Load exercises** từ lesson
3. **Load unit quiz** từ unit
4. **Handle mixed content types**

### Data Models cần update:
```kotlin
data class LessonContent(
    val questions: List<Question>,           // Practice questions
    val listeningExercises: List<Exercise>,  // Listening activities  
    val speakingExercises: List<Exercise>,   // Speaking activities
    val writingExercises: List<Exercise>,    // Writing activities
    val unitQuiz: Quiz?                      // Unit test (optional)
)
```

## ✅ Migration Checklist

- [ ] Backup database
- [ ] Run migration script
- [ ] Verify data integrity
- [ ] Test existing APIs
- [ ] Update new APIs
- [ ] Update Android app
- [ ] Test end-to-end flow
- [ ] Deploy to production

## 🎉 Kết quả mong đợi

Sau migration:
1. **Questions** có thể thuộc về **lesson** trực tiếp
2. **Quizzes** có thể thuộc về **unit** (final tests)
3. **Mixed content** trong lessons (questions + exercises)
4. **Backward compatibility** với existing system
5. **Better performance** với new indexes
6. **Easier querying** với new views
