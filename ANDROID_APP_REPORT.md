# Báo cáo kiến trúc Android app `seoulhankukobook`

```mermaid
flowchart LR
    subgraph Presentation
        Screens[Compose Screens]
        Components[Reusable Components]
        Navigation[Navigation Graph]
    end
    subgraph ViewModel
        VM[Hilt ViewModel]
        StateFlow[StateFlow + UIState]
    end
    subgraph Domain
        UseCase[Use Cases]
        Models[Domain Models]
    end
    subgraph Data
        Repo[Repositories]
        Remote[Retrofit API]
        Local[Room + DataStore]
        Mapper[ExceptionMapper]
    end

    Screens --> VM --> UseCase --> Repo
    Repo --> Remote
    Repo --> Local
    Repo -->|ML| MLPredictor[TFLite (optional)]
```

---

## Luồng điều hướng chính

```mermaid
flowchart TD
    Splash(Splash/Token Check)
    Login(Login Screen)
    Home(Home Dashboard)
    Course(Course -> Units)
    Lesson(Lesson Flow Pager)
    Writing(Writing Practice)
    Speaking(Listening/Speaking)
    Leaderboard(Leaderboard & Quests)

    Splash -->|Auth ok| Home
    Splash -->|Unauthorized| Login
    Login --> Home
    Home --> Course --> Lesson
    Lesson -->|Quiz done| Home
    Lesson -->|Writing tasks| Writing
    Home --> Leaderboard
```

- `LoginScreen` quan sát `AuthViewModel.authState`.
- `ModernHomeScreen` lấy courses/streak từ `HomeViewModel`.
- `LessonFlowScreen` điều phối pager quiz, XP, TTS.

---

## Luồng dữ liệu & API

```mermaid
sequenceDiagram
    participant UI as Compose UI
    participant VM as ViewModel
    participant Repo as Repository
    participant API as Retrofit API
    participant Local as Room/DataStore

    UI->>VM: intent (login/course/quiz)
    VM->>Repo: thực thi use case
    Repo->>API: gọi REST (Bearer token)
    Repo->>Local: cache kết quả
    API-->>Repo: Response<Result>
    Repo-->>VM: Result + mapped error
    Local-->>Repo: data offline
    VM-->>UI: StateFlow<Uistate>
```

- `AuthInterceptor` tự đính token & refresh khi 401.
- Mọi repository trả `Result<T>` kèm lỗi domain (`AppException`).

---

## Inference nét chữ

```mermaid
flowchart LR
    Canvas[Stroke Canvas] --> Preprocess[Normalize & Rasterize]
    Preprocess -->|Offline| TFLiteDevice[On-device TFLite]
    Preprocess -->|Online| APIStroke[/POST /v1/predict-stroke/]
    APIStroke --> BackendTFLite[TFLite Runtime]
    BackendTFLite --> Result[Prediction + Confidence]
    TFLiteDevice --> Result
```

- Mặc định: gọi backend qua `MLPredictionRepository`.
- Định hướng offline:
  - Hilt cung cấp `Interpreter`.
  - `LocalStrokePredictor` → `PredictCharacterUseCase`.
  - Chiến lược hybrid: ưu tiên on-device, fallback API.

---

## Checklist cải tiến

- [ ] Hoàn thiện module on-device TFLite + asset pipeline.
- [ ] Chuẩn hóa UI state (Loading/Error) với `sealed class`.
- [ ] Bổ sung test UI Compose và integration repository.
- [ ] Đồng bộ analytics (streak, XP) vào dashboard.

