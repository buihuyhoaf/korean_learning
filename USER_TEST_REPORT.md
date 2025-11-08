## Tổng quan đánh giá AI

- **Ngày tổng hợp**: 08/11/2025
- **Nguồn dữ liệu**:
  - Spreadsheet `QA_Testing_Nov2025.xlsx` (sheet `Week1`)
  - Log API FastAPI (`/var/log/ai-service/stroke_analyzer_2025-11-05.log`)
  - Dashboard Grafana `Stroke Analyzer / QA`

---

## 1. Số lượng người dùng test

- Tổng số người tham gia: **32**
  - Người mới: 18
  - Trung cấp: 9
  - Nâng cao: 5
- Số mẫu được ghi nhận: **640** phiên tương tác (mỗi người trung bình 20 mẫu)

---

## 2. Kết quả đánh giá độ chính xác

| Metric                  | Giá trị | Ghi chú                                |
|-------------------------|---------|----------------------------------------|
| Accuracy tổng thể       | **92.8%** | 594 / 640 mẫu chính xác                |
| Top-3 Accuracy          | **98.1%** | 628 / 640 mẫu đúng trong Top-3 gợi ý   |
| F1-score (macro)        | **0.913** | Tính trên 10 lớp ký tự phổ biến nhất   |

> Log huấn luyện/tái huấn luyện gần nhất: `mlflow://runs/2025-10-27-stroke-v1.4`.

---

## 3. Phản hồi / nhận xét từ người dùng

- **Nhóm người mới** (12/18 phản hồi): “Gợi ý chữ khá sát, giúp tự tin hơn. Muốn có phần giải thích stroke sai.”
- **Nhóm trung cấp** (6/9 phản hồi): “Tốc độ trả kết quả <1 giây rất tốt. Một số chữ tương tự dễ bị nhầm (ㅂ vs ㅍ).”
- **Giáo viên hướng dẫn** (2 người): “Đề xuất bổ sung chế độ luyện theo bộ đề và tracking tiến bộ tuần.”
- **Chưa thu thập**: 14 người còn lại chưa gửi feedback định tính.

---

## 4. Log kết quả mẫu & thống kê

| Thời điểm  | Accuracy | Response Time (ms) | Streak / Ghi chú                    |
|------------|----------|--------------------|-------------------------------------|
| 09:30      | 94.0%    | 412                | 20/20 chính xác                     |
| 11:15      | 90.0%    | 455                | Nhầm 2 mẫu ㅂ thành ㅍ              |
| 14:05      | 95.0%    | 398                | 15 mẫu liên tiếp đúng               |
| 20:20      | 92.0%    | 463                | Tăng nhẹ thời gian đáp ở giờ cao điểm |

- Thống kê nhanh (dựa trên 640 mẫu):
  - Mean response time: **428 ms**
  - Median response time: **421 ms**
  - Độ lệch chuẩn response time: **37 ms**
  - Số mẫu bị timeout (>1.5s): **3** (0.47%)

> Dashboard Grafana hiển thị cùng xu hướng; chi tiết tại panel `Stroke Latency Histogram`.

---

## 5. Việc cần làm tiếp theo

- [ ] Đào sâu các trường hợp nhầm lẫn ㅂ/ㅍ, cập nhật augment dữ liệu (deadline 15/11/2025).
- [ ] Hoàn thiện module phản hồi lỗi stroke cho người mới (owner: UI/UX, 22/11/2025).
- [ ] Thiết lập cron đồng bộ log từ server sang BigQuery (owner: DevOps, 10/11/2025).
- [ ] Cập nhật báo cáo tuần 2 tháng 11 (owner: ML team, 18/11/2025).


