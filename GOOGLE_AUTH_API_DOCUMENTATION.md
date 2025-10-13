# Google Authentication API Documentation

## 📋 Tổng quan

API đăng nhập/đăng ký bằng Google đã được triển khai thành công cho backend FastAPI của project korean_learning.

## 🏗️ Cấu trúc đã triển khai

### 1. Dependencies đã thêm
```toml
# pyproject.toml
"google-auth>=2.29.0",
```

### 2. Configuration
- **File**: `src/app/core/config.py`
- **Thêm**: `GoogleAuthSettings` class với `GOOGLE_CLIENT_ID`
- **Default**: `461063240681-n6ffjuabhskh1q0udhotlldol4k7mdga.apps.googleusercontent.com`

### 3. Database Model
- **File**: `src/app/models/user.py`
- **Thêm field**: `picture: Mapped[str | None] = mapped_column(String(500), nullable=True)`
- **Migration**: `add_picture_field_to_users.py`

### 4. Google Auth Helper
- **File**: `src/app/core/google_auth.py`
- **Functions**:
  - `verify_google_token()`: Xác minh Google ID token
  - `extract_username_from_email()`: Tạo username từ email
  - `generate_password_for_google_user()`: Tạo password ngẫu nhiên

### 5. Schemas
- **File**: `src/app/schemas/google_auth.py`
- **Models**:
  - `GoogleSignInRequest`: Request schema
  - `GoogleSignInResponse`: Response schema
  - `GoogleUserInfo`: User info schema
  - `GoogleAuthError`: Error response schema

### 6. API Endpoint
- **File**: `src/app/api/v1/google_auth.py`
- **Endpoint**: `POST /api/v1/auth/google`
- **Router**: Đã được include vào main API router

## 🚀 API Usage

### Endpoint: `POST /api/v1/auth/google`

#### Request
```json
{
  "id_token": "GOOGLE_ID_TOKEN_FROM_ANDROID"
}
```

#### Response Success (200)
```json
{
  "access_token": "JWT_TOKEN_VALID_FOR_7_DAYS",
  "token_type": "bearer"
}
```

#### Response Error (400)
```json
{
  "detail": "Invalid Google ID token"
}
```

#### Response Error (500)
```json
{
  "detail": "Internal server error during Google authentication"
}
```

## 🔧 Setup Instructions

### 1. Environment Variables
Thêm vào file `.env`:
```env
GOOGLE_CLIENT_ID=461063240681-n6ffjuabhskh1q0udhotlldol4k7mdga.apps.googleusercontent.com
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days in minutes
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 2. Database Migration
Chạy migration để thêm field `picture`:
```bash
cd src
alembic upgrade head
```

### 3. Install Dependencies
```bash
pip install google-auth>=2.29.0
```

## 🔄 Flow hoạt động

1. **Android app** gửi Google ID token đến `/api/v1/auth/google`
2. **Backend** xác minh token với Google API
3. **Nếu token hợp lệ**:
   - Lấy thông tin user (email, name, picture) từ token payload
   - Kiểm tra user đã tồn tại trong DB chưa
   - **Nếu chưa tồn tại**: Tạo user mới với random password
   - **Nếu đã tồn tại**: Cập nhật name và picture nếu thay đổi
4. **Tạo JWT token** với thời hạn 7 ngày
5. **Trả về** access_token và token_type

## 🛡️ Security Features

### Token Validation
- Xác minh Google ID token với Google API
- Kiểm tra `aud` (audience) phải khớp với `GOOGLE_CLIENT_ID`
- Xác minh email đã được verify

### User Creation
- Tự động tạo username từ email
- Xử lý trường hợp username đã tồn tại (thêm số)
- Tạo password ngẫu nhiên cho Google users
- Hash password bằng bcrypt

### JWT Token
- Thời hạn 7 ngày (có thể config)
- Sử dụng SECRET_KEY từ environment
- Algorithm: HS256

## 📊 Database Schema

### Users Table (Updated)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    picture VARCHAR(500),  -- NEW FIELD
    role VARCHAR(20) DEFAULT 'student',
    exp INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tier_id INTEGER REFERENCES tier(id)
);
```

## 🧪 Testing

### Test với cURL
```bash
# Test với valid Google ID token
curl -X POST "http://localhost:8000/api/v1/auth/google" \
  -H "Content-Type: application/json" \
  -d '{"id_token": "YOUR_GOOGLE_ID_TOKEN"}'

# Expected response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Test với invalid token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/google" \
  -H "Content-Type: application/json" \
  -d '{"id_token": "invalid_token"}'

# Expected response:
{
  "detail": "Invalid Google ID token"
}
```

## 🔗 Integration với Android

### Android Side
```kotlin
// Gửi request đến backend
val request = GoogleSignInRequest(idToken = googleIdToken)
val response = apiService.signInWithGoogle(request)

// Response sẽ chứa JWT token
val accessToken = response.accessToken
val tokenType = response.tokenType
```

### Backend Response Format
Response format hoàn toàn tương thích với yêu cầu Android app:
- `access_token`: JWT token có thể sử dụng cho các API khác
- `token_type`: Luôn là "bearer"

## 📝 Error Handling

### Common Errors
1. **400 Bad Request**: Invalid Google ID token
2. **500 Internal Server Error**: Database error hoặc Google API error

### Error Response Format
```json
{
  "detail": "Error message description"
}
```

## 🚀 Deployment Notes

### Production Setup
1. **Environment Variables**: Cập nhật tất cả sensitive values
2. **Database**: Chạy migration trên production DB
3. **Google Client ID**: Đảm bảo đúng client ID cho production
4. **HTTPS**: Sử dụng HTTPS cho production
5. **Rate Limiting**: Cấu hình rate limiting phù hợp

### Monitoring
- Log tất cả Google auth attempts
- Monitor JWT token creation
- Track user creation/update events
- Monitor error rates

## 📚 References

- [Google ID Token Verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
- [FastAPI Authentication](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Google Auth Library](https://google-auth.readthedocs.io/)
- [JWT with Python-JOSE](https://python-jose.readthedocs.io/)

---

**Lưu ý**: API đã sẵn sàng sử dụng với Android app. Chỉ cần setup environment variables và chạy database migration.


