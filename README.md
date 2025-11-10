# Korean Learning FastAPI Backend – Firebase Push Notifications

## Firebase cấu hình
- Đặt biến môi trường `FIREBASE_SERVICE_ACCOUNT_B64` trên Render Dashboard (hoặc `.env` cục bộ).
- Script `deploy.sh` tự động giải mã và export biến `GOOGLE_APPLICATION_CREDENTIALS` trỏ tới file JSON.
- Module `src/app/core/firebase.py` khởi tạo Firebase Admin SDK khi ứng dụng khởi động. Nếu thiếu file hoặc env, các API push sẽ trả về HTTP 503.

## Endpoint mới
```
POST /api/v1/push-tokens/register
{
  "token": "FCM_DEVICE_TOKEN",
  "platform": "android"
}

DELETE /api/v1/push-tokens/unregister
{
  "token": "FCM_DEVICE_TOKEN"
}

POST /api/v1/notifications/send
{
  "user_ids": ["<uuid-1>", "<uuid-2>"],
  "title": "Test notification",
  "body": "Hello from admin!"
}
```
- Endpoint `/notifications/send` yêu cầu tài khoản có `role=admin` hoặc `is_superuser=true`.
- Response gồm thông tin số token gửi thành công/thất bại.

## Admin UI – Gửi Push Notification
- Đăng nhập trang admin (`/admin`), mở mục **Push Notifications** từ navigation (đường dẫn: `/admin/push-notifications`).
- Tìm kiếm người dùng (username/email) và thêm vào danh sách nhận. Có thể xoá từng người trước khi gửi.
- Nhập tiêu đề, nội dung và nhấn **Gửi thông báo**. Kết quả sẽ hiển thị số token thành công/thất bại.
- Nếu Firebase chưa cấu hình đúng, màn hình sẽ báo `Firebase not initialized`.

## Kiểm thử
```
uv run pytest tests/test_push_service.py
```

## Triển khai
1. Cập nhật các biến môi trường trên Render.
2. Deploy lại service để build Docker mới.
3. Gửi thử thông báo qua endpoint admin và kiểm tra thiết bị Android nhận FCM.


