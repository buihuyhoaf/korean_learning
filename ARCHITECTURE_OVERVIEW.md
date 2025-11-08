## Kiến Trúc Tổng Quan

### Tổng thể

```
Android App (Jetpack Compose, ViewModel, Repository, TFLite)
        │  HTTPS (REST/JSON, OAuth2 + JWT, Retrofit)
        ▼
FastAPI Backend (ASGI, Dependency Injection, Background Tasks, ML Gateway)
        │  async SQLAlchemy / psycopg2-binary
        ▼
PostgreSQL (RDBMS, schema hóa khóa học, user, gamification, logging)
        │
        └─ TensorFlow Lite (.tflite model, deploy on-device & server-side runtime)
```

- **Android client**: xây dựng với Jetpack Compose, mô hình MVVM + Repository. Ứng dụng chịu trách nhiệm tương tác người dùng, caching cục bộ (Room, DataStore), quản lý trạng thái, và trong một số luồng chạy trực tiếp TensorFlow Lite để phản hồi tức thì.
- **FastAPI backend**: cung cấp API REST, xác thực OAuth2/JWT, điều phối nghiệp vụ, giao tiếp với PostgreSQL, và đóng vai trò gateway cho inference TFLite phía server. Sử dụng dependency injection, middleware, background worker (Celery/RQ tùy cấu hình) để xử lý tác vụ dài hạn.
- **PostgreSQL**: lưu dữ liệu bền vững, thiết kế schema normalization cho user, khóa học, bài học, câu hỏi, đáp án, tiến trình, gamification, bảng token, log AI. Alembic quản lý migration.
- **TensorFlow Lite**: mô hình `.tflite` được huấn luyện offline rồi đóng gói. Có thể:
  - Đẩy xuống thiết bị để inference offline/on-device.
  - Deploy trên server, nạp bằng `tflite-runtime` để xử lý các yêu cầu cần tài nguyên lớn hoặc muốn kiểm soát phiên bản mô hình tập trung.

### Liên kết & bảo mật

- Giao tiếp Android ↔ FastAPI thông qua HTTPS, mọi request (trừ route công khai) đi kèm `Authorization: Bearer <access_token>`. Refresh token lưu an toàn trong DataStore và được rotate tại backend.
- FastAPI sử dụng rate limiting, cache, exception handler tùy chỉnh (`core/middleware`, `core/exceptions`) để bảo vệ dịch vụ.
- PostgreSQL có thể cài đặt replication (read replica) và backup định kỳ; kết nối được quản lý qua pool async để tối ưu chi phí mở/kết thúc phiên.

## Cấu Trúc Thư Mục Chính

### Backend (`/Users/buihoa/PycharmProjects/korean_learning/src/app`)

- `main.py`: tạo ứng dụng FastAPI, đăng ký router, middleware (CORS, client cache), mount static & admin.
- `api/`
  - `v1/`: tuyến API phiên bản 1. Mỗi file tách theo domain:  
    - `login.py`, `logout.py`, `google_auth.py`: xác thực, token management.  
    - `course_management.py`, `exercises.py`, `user_progress.py`: điều phối học liệu, câu hỏi và tiến trình.  
    - `predict.py`, `badges.py`, `leaderboard.py`, `tiers.py`, `friends.py`: gamification, social, AI dự đoán.  
  - `routes/stroke_api.py`: route chuyên sâu cho phân tích nét chữ (handwriting), nhận payload stroke, validate, gọi service ML.
- `core/`
  - `config.py`: cấu hình môi trường, biến môi trường (DB URI, secret, ML path).  
  - `db/database.py`: khởi tạo engine async, session, transaction context.  
  - `security.py`: util OAuth2, JWT, hashing Bcrypt, quản lý refresh token rotation.  
  - `worker/`: cấu hình cho background tasks (ví dụ gửi email, pipeline ML).  
  - `utils/`: cache Redis, rate limit, queue, tích hợp Supabase.  
  - `logger.py`: cấu hình logging (console/file), hook debug.
- `crud/`: pattern CRUD thuần (tách biệt với service/logic) giúp FastAPI giữ controller mỏng. Ví dụ: `crud_users.py`, `progress_tracking.py`, `exercise.py`.
- `models/`: SQLAlchemy ORM mapping. Bao gồm các bảng domain: user, khóa học, question_xxx (matching, pronunciation, sentence order), gamification (badge, tier), notification, social, ai_log.
- `schemas/`: Pydantic schema cho request/response, đồng bộ với `models`.
- `ml/`: module riêng cho ML  
  - `model_loader.py`, `tflite_loader.py`: nạp model `.tflite`, quản lý phiên bản, caching.  
  - `preprocessor.py`: chuẩn hóa dữ liệu đầu vào (stroke normalization, encode audio).  
  - `README.md`: hướng dẫn pipeline training & deploy.
- `services/`: layer nghiệp vụ phức tạp ngoài CRUD, điển hình `stroke_analyzer.py` kết hợp preprocessor + inference.
- `admin/`: tích hợp FastAPI-Admin/Custom, template HTML theo dõi tiến trình, upload nội dung.
- `middleware/`: custom middleware (client cache header).
- `scripts/`: util CLI (tạo superuser, seed dữ liệu, thiết lập tier).  
- `migrations/`: Alembic migration (schema versioning).
- Files hỗ trợ khác: `docker-compose.yml`, `Dockerfile`, `render.yaml`, `UV.lock` phục vụ deploy.

### Frontend Android (`/Users/buihoa/AndroidStudioProjects/seoul_hankuko_book/app/src/main/java/com/seoulhankuko/app`)

- `data/`
  - `api/`  
    - `NetworkModule.kt`: cấu hình Retrofit, OkHttp, base URL, logging interceptor.  
    - `AuthInterceptor.kt`: thêm Authorization header, handle 401 → refresh token.  
    - `service/ApiService.kt`: định nghĩa endpoint đối xứng với FastAPI.  
    - `model/`: DTO mapping JSON ↔ Kotlin data class (Auth, Course, Stroke, Prediction…).  
    - `util/ExceptionMapper.kt`: ánh xạ lỗi HTTP → domain error.
  - `database/`: Room  
    - `AppDatabase`, `DatabaseModule`: cấu hình Hilt, type converter.  
    - DAOs (`CourseDao`, `UnitDao`, …) + entities/relationship (cache offline).
  - `local/`: DataStore (preferences) để giữ token, thiết lập người dùng, cài đặt cá nhân.
  - `repository/`: mỗi domain một repository (Auth, Course, EntryTest, Quiz, StrokeAnalysis, UserProgress, Gamification...) kết hợp remote + local + business logic.
- `domain/`
  - `model/`: lớp thuần Kotlin đại diện cho entity trong app (CourseWithUnits, HangulChar, StrokePattern...).  
  - `usecase/`: xử lý nghiệp vụ thuần, ví dụ: `AnalyzeStrokesUseCase`, `StrokeComparator`, `StrokeAutoCorrector`, `PredictCharacterUseCase`.
  - `exception/`: chuẩn hoá exception domain.
- `presentation/`
  - `screens/`: Compose UI cho từng chu trình (LoginScreen, LessonFlowScreen, WritingScreen, SpeakingScreen, LeaderboardScreen...).  
  - `components/`: UI components (MatchingQuestionCard, EntryTestReminderDialog, GoogleSignInButton, Audio/TTS manager).  
  - `viewmodel/`: ViewModel (Hilt injected) điều phối state mỗi màn hình.  
  - `util`, `ui/theme`: style, màu sắc, typography.
- `core/`: logging chung (`Logger.kt`, `LoggingModule.kt`).  
- `di/`: Hilt module cho canvas/ML.  
- `ui/screen/canvas`: custom view cho handwriting, xử lý gesture, convert nét sang format feed vào ML.
- `MainActivity.kt`, `navigation/`: entry point, Graph điều hướng màn hình.

## Luồng Nghiệp Vụ Chính & Chi Tiết

### 1. Đăng nhập & Làm mới token

1. Người dùng nhập username/email + password trên `LoginScreen`; `AuthViewModel` gọi `AuthRepository.login()`.
2. Retrofit gửi `POST /api/v1/login` (body x-www-form-urlencoded chuẩn OAuth2).
3. `login.py` xác thực:  
   - `authenticate_user()` kiểm tra user tồn tại, password hash đúng.  
   - `create_access_token()` tạo JWT (HS256, payload chứa `sub`, `exp`).  
   - `create_refresh_token_with_storage()` sinh refresh token, hash & lưu vào bảng `user_refresh_token`.
4. Response trả về cặp token, app lưu tại `UserPreferencesManager` (DataStore) và emit state `AuthState.Authenticated`.
5. `AuthInterceptor` đính access token vào header cho mọi request.
6. Khi server trả 401 do token hết hạn:  
   - Interceptor trigger flow refresh: gửi `POST /api/v1/login/refresh` với refresh token (body JSON).  
   - `refresh_access_token` xác thực refresh token (kiểm tra blacklist, signature), rotate token: hủy token cũ, tạo token mới, cập nhật DB.  
   - App cập nhật DataStore, retry request ban đầu minh bạch với người dùng.
7. Người dùng logout → `AuthRepository.logout()` gọi `POST /api/v1/logout`, backend `invalidate_user_refresh_tokens` đánh dấu refresh token hết hiệu lực.

### 2. Đăng nhập Google (OAuth)

1. App dùng Google Sign-In SDK nhận `idToken`.  
2. `GoogleSignInRepository.authenticate()` gửi `POST /api/v1/google_auth/login` chứa token và thông tin thiết bị.  
3. Backend xác minh token qua Google API, tìm hoặc tạo user tương ứng, ánh xạ thông tin profile.  
4. Hệ thống tạo access/refresh token giống flow thường và trả về.  
5. App đồng bộ state, lưu refresh token, hiển thị hồ sơ Google trong `ProfileScreen`.

### 3. Khởi động ứng dụng & Đồng bộ dữ liệu

1. `SplashActivity` kiểm tra token, prefetch thông tin tài khoản (`LoggedAccountDao`).  
2. `HomeViewModel` gọi `CourseRepository.syncCourses()`:  
   - Kiểm tra dữ liệu cache (Room); nếu quá hạn → gọi `GET /api/v1/course_management/courses`.  
   - Backend gom dữ liệu course/unit/lesson, có thể dùng join view (migration `create_lesson_content_views`).  
   - Data mới lưu Room (DAO `CourseDao`, `UnitDao`) và emit UI.  
3. Đồng bộ tiến trình (`UserProgressRepository.fetchProgress()` ↔ `api/v1/user_progress.py`), leaderboard (`LeaderboardRepository` ↔ `leaderboard.py`), daily goals (`daily_goals.py`).

### 4. Làm bài học & Quiz đa dạng

1. `LessonFlowScreen` tải lesson detail qua `LessonRepository.getLessonFlow`, gồm danh sách `LessonTask`.  
2. Người học tương tác các dạng câu hỏi (multiple choice, fill-in, matching, listening, speaking).  
3. Khi submit:  
   - `QuizRepository.submitAnswer()` gửi payload tới endpoint tương ứng (`POST /api/v1/exercises/{id}/answer`).  
   - `exercises.py` xác định loại câu hỏi → ủy thác tới `crud/question_crud.py` hoặc service specific.  
   - Điểm số, feedback, phần thưởng (XP, coin) được tính; `crud/progress_tracking.py` cập nhật bảng `user_answer`, `user_progress`, `gamification`.  
   - Event quan trọng ghi vào `models/ai_log.py` nếu có AI scoring.  
4. Backend trả response giàu thông tin: kết quả, xp kiếm được, chuỗi streak, gợi ý lesson tiếp theo.  
5. App cập nhật UI, hiển thị animation (ví dụ `StreakCelebrationScreen`), và lưu offline state.

### 5. Entry Test / Placement

1. `EntryTestScreen` hiển thị bài test: question mix 4 kỹ năng.  
2. Câu trả lời tạm lưu cục bộ để resume; khi hoàn tất → `EntryTestRepository.submit()` gửi tới `api/v1/entry_test.py`.  
3. Backend tính điểm dựa trên trọng số từng dạng câu hỏi, hỗ trợ AI scoring nếu cần (gọi `ml` module).  
4. Kết quả ghi vào bảng `entry_test`, đề xuất cấp độ (Beginner/Intermediate/Advanced) và unlock nội dung phù hợp.  
5. `EntryTestResultScreen` đọc response, hiển thị biểu đồ (các kỹ năng), gợi ý lộ trình học.

### 6. Phân tích chữ viết tay / Stroke Evaluation

**On-device (offline-first)**

1. `WritingScreen` thu nét từ canvas (`StrokePath`, `StrokePoint`).  
2. `AnalyzeStrokesUseCase` chuẩn hóa nét (scale, align, resample).  
3. `PredictCharacterUseCase` nạp model `.tflite` từ assets (thông qua `MLPredictionRepository`).  
4. TensorFlow Lite interpreter chạy inference, trả xác suất các kí tự, sai lệch nét.  
5. UI hiển thị heatmap, highlight nét sai, gợi ý sửa. Kết quả có thể lưu cục bộ và sync khi online.

**Server-side (central inference)**

1. Khi cần đánh giá chất lượng cao hoặc cập nhật mô hình thường xuyên, app gửi `POST /api/routes/stroke_api.py` với payload JSON (stroke list, metadata).  
2. Backend:  
   - Xác thực, kiểm tra quota/rate limit (để tránh lạm dụng).  
   - `stroke_analyzer.py` gọi `preprocessor` (normalize, quantize).  
   - `tflite_loader.py` tải model theo phiên bản (metadata lưu trong PostgreSQL).  
   - `tflite-runtime` thực thi, kết quả được chuẩn hóa thành score, confidence, feedback text.  
   - Ghi log `ai_log` (user_id, lesson_id, kết quả) để phục vụ analytics hoặc re-training.  
3. Response trả về cho app: điểm chi tiết, danh sách nét sai, gợi ý luyện tập.

### 7. Gamification & Social

1. `LeaderboardScreen` gọi `GET /api/v1/leaderboard` → backend tổng hợp điểm (tuần/tháng) từ bảng `user_progress` và `gamification`.  
2. `QuestsScreen` lấy nhiệm vụ hằng ngày (`daily_goals.py`), phần thưởng (`tiers.py`, `badges.py`).  
3. `ShopScreen` hiển thị vật phẩm (lưu trong bảng `tier`/`reward`) với yêu cầu coin.  
4. Hệ thống bạn bè (`friends.py`): gửi lời mời, chấp nhận, theo dõi tiến trình.  
5. Notifications (`user_notifications.py`) gửi về app, hiển thị trong `HomeViewModel`, đồng bộ trạng thái đọc về server.

### 8. Quản trị & Vận hành

1. `app/admin`: giao diện web (FastAPI-Admin) cho quản trị viên.  
2. Quản trị viên có thể tạo khóa học, upload bài tập, xem thống kê tiến trình, theo dõi lỗi AI (truy cập log).  
3. File `custom_assets.py` thêm JS/CSS custom, biểu đồ tiến trình.  
4. Script trong `scripts/` hỗ trợ tạo superuser, seed question types; chạy qua CLI hoặc trong quá trình deploy.  
5. Logging (`logs/app.log`) lưu lịch sử truy cập, lỗi; có thể tích hợp stack ELK hoặc APM.

---

Tài liệu này nhằm phục vụ viết báo cáo, có thể mở rộng bằng sơ đồ sequence (PlantUML), ma trận module, hoặc checklist triển khai (deploy, CI/CD) khi cần.

