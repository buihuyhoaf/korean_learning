# Korean Learning Database Schema Overview

## 📊 Tổng quan các Table và Relationship

### 🏗️ Core Tables

#### 1. **User Management**
- **`users`** - Bảng người dùng chính
  - `id` (PK), `username`, `email`, `password`, `picture`, `role`, `exp`, `streak_days`, `created_at`, `tier_id` (FK)
  - Relationships: 13 relationships với các bảng khác

- **`tier`** - Bảng phân cấp người dùng
  - `id` (PK), `name`, `created_at`, `updated_at`
  - Relationships: 1 relationship với `users`

#### 2. **Course Structure**
- **`courses`** - Khóa học
  - `id` (PK), `title`, `description`, `order_index`, `created_at`
  - Relationships: 2 relationships với `units` và `user_course_progress`

- **`units`** - Đơn vị học
  - `id` (PK), `course_id` (FK), `title`, `description`, `order_index`, `created_at`
  - Relationships: 3 relationships với `course`, `lessons`, `user_unit_progress`

- **`lessons`** - Bài học
  - `id` (PK), `unit_id` (FK), `title`, `description`, `order_index`, `created_at`
  - Relationships: 6 relationships với `unit`, `quizzes`, exercises, `user_lesson_progress`

#### 3. **Quiz System**
- **`quizzes`** - Bài kiểm tra
  - `id` (PK), `lesson_id` (FK), `title`, `description`, `type`, `order_index`, `created_at`
  - Relationships: 3 relationships với `lesson`, `questions`, `user_quiz_attempts`

- **`question_types`** - Loại câu hỏi
  - `id` (PK), `name`, `description`
  - Relationships: 1 relationship với `questions`

- **`questions`** - Câu hỏi
  - `id` (PK), `quiz_id` (FK), `question_type_id` (FK), `content`, `audio_url`, `image_url`, `correct_answer`, `explanation`, `order_index`, `created_at`
  - Relationships: 5 relationships với `quiz`, `question_type`, `options`, `user_question_attempts`, `user_question_errors`

- **`question_options`** - Lựa chọn câu trả lời
  - `id` (PK), `question_id` (FK), `option_text`, `is_correct`, `created_at`
  - Relationships: 1 relationship với `question`

#### 4. **Exercise Types**
- **`listening_exercises`** - Bài tập nghe
  - `id` (PK), `lesson_id` (FK), `audio_url`, `transcript`, `description`, `created_at`
  - Relationships: 1 relationship với `lesson`

- **`speaking_exercises`** - Bài tập nói
  - `id` (PK), `lesson_id` (FK), `prompt`, `sample_answer`, `created_at`
  - Relationships: 1 relationship với `lesson`

- **`writing_exercises`** - Bài tập viết
  - `id` (PK), `lesson_id` (FK), `prompt`, `sample_answer`, `created_at`
  - Relationships: 1 relationship với `lesson`

### 📈 Progress Tracking Tables

#### 5. **User Progress**
- **`user_course_progress`** - Tiến độ khóa học
  - `id` (PK), `user_id` (FK), `course_id` (FK), `completed_at`, `is_completed`, `progress_percent`
  - Relationships: 2 relationships với `user`, `course`

- **`user_unit_progress`** - Tiến độ đơn vị học
  - `id` (PK), `user_id` (FK), `unit_id` (FK), `completed_at`, `is_completed`, `progress_percent`
  - Relationships: 2 relationships với `user`, `unit`

- **`user_lesson_progress`** - Tiến độ bài học
  - `id` (PK), `user_id` (FK), `lesson_id` (FK), `completed_at`, `is_completed`, `progress_percent`
  - Relationships: 2 relationships với `user`, `lesson`

#### 6. **Quiz Attempts**
- **`user_quiz_attempts`** - Lần làm bài kiểm tra
  - `id` (PK), `user_id` (FK), `quiz_id` (FK), `completed_at`, `score`, `exp_earned`, `started_at`
  - Relationships: 3 relationships với `user`, `quiz`, `user_question_attempts`

- **`user_question_attempts`** - Lần trả lời câu hỏi
  - `id` (PK), `user_quiz_attempt_id` (FK), `question_id` (FK), `user_answer`, `is_correct`, `answered_at`
  - Relationships: 2 relationships với `quiz_attempt`, `question`

- **`user_question_errors`** - Lỗi câu hỏi
  - `id` (PK), `user_id` (FK), `question_id` (FK), `last_wrong_answer`, `last_wrong_at`, `error_count`
  - Relationships: 2 relationships với `user`, `question`

### 🎮 Gamification Tables

#### 7. **Experience & Rewards**
- **`user_exp_log`** - Lịch sử kinh nghiệm
  - `id` (PK), `user_id` (FK), `source`, `amount`, `created_at`
  - Relationships: 1 relationship với `user`

- **`badges`** - Huy hiệu
  - `id` (PK), `name`, `description`, `icon_url`, `created_at`
  - Relationships: 1 relationship với `user_badges`

- **`user_badges`** - Huy hiệu người dùng
  - `id` (PK), `user_id` (FK), `badge_id` (FK), `earned_at`
  - Relationships: 2 relationships với `user`, `badge`
  - Unique constraint: `user_id`, `badge_id`

#### 8. **Goals & Challenges**
- **`daily_goals`** - Mục tiêu hàng ngày
  - `id` (PK), `user_id` (FK), `target_exp`, `target_lessons`, `created_at`, `is_completed`
  - Relationships: 1 relationship với `user`

- **`challenges`** - Thử thách
  - `id` (PK), `title`, `description`, `start_date`, `end_date`, `exp_reward`
  - Relationships: 1 relationship với `user_challenges`

- **`user_challenges`** - Thử thách người dùng
  - `id` (PK), `user_id` (FK), `challenge_id` (FK), `completed_at`, `progress_percent`, `is_completed`
  - Relationships: 2 relationships với `user`, `challenge`

### 👥 Social Features

#### 9. **Social System**
- **`friends`** - Bạn bè
  - `id` (PK), `user_id` (FK), `friend_user_id` (FK), `status`, `created_at`
  - Relationships: 2 relationships với `user` (as user và friend)
  - Unique constraint: `user_id`, `friend_user_id`

- **`leaderboard`** - Bảng xếp hạng
  - `id` (PK), `user_id` (FK), `season`, `rank`, `exp`, `updated_at`
  - Relationships: 1 relationship với `user`

### 🤖 AI & Analytics

#### 10. **AI Integration**
- **`ai_logs`** - Log AI
  - `id` (PK), `user_id` (FK), `exercise_type`, `input_url`, `recognized_text`, `confidence`, `result`, `created_at`
  - Relationships: 1 relationship với `user`

#### 11. **Notifications**
- **`notifications`** - Thông báo
  - `id` (PK), `user_id` (FK), `title`, `message`, `type`, `is_read`, `created_at`
  - Relationships: 1 relationship với `user`

### ⚙️ System Tables

#### 12. **Rate Limiting**
- **`rate_limit`** - Giới hạn tốc độ
  - `id` (PK), `tier_id` (FK), `name`, `path`, `limit`, `period`, `created_at`, `updated_at`
  - Relationships: 1 relationship với `tier`

## 🔗 Relationship Summary

### **User Table** (Central Hub)
- **13 relationships** với các bảng khác:
  - `course_progress`, `unit_progress`, `lesson_progress`
  - `quiz_attempts`, `question_errors`
  - `exp_logs`, `badges`, `daily_goals`, `challenges`
  - `friends` (2 relationships), `leaderboard`, `ai_logs`, `notifications`

### **Course Hierarchy**
- `courses` → `units` → `lessons` → `quizzes` → `questions` → `question_options`
- `lessons` → `listening_exercises`, `speaking_exercises`, `writing_exercises`

### **Progress Tracking Chain**
- `user_course_progress` → `user_unit_progress` → `user_lesson_progress`
- `user_quiz_attempts` → `user_question_attempts`

### **Gamification Chain**
- `user_exp_log` ← `user_quiz_attempts`, `daily_goals`, `challenges`
- `user_badges` ← `badges`
- `leaderboard` ← `user` (exp)

## 📊 Statistics
- **Total Tables**: 22 tables
- **Total Relationships**: 45+ relationships
- **Core Entity**: User (13 relationships)
- **Hierarchical Structure**: Course → Unit → Lesson → Quiz → Question
- **Gamification**: 6 tables for rewards, goals, and challenges
- **Social Features**: 2 tables for friends and leaderboard
- **AI Integration**: 1 table for AI logs
- **System Features**: 2 tables for notifications and rate limiting

