# Phiên thu thật 02 — 08/11/2026

## Bằng chứng và phạm vi

Nguồn `firmware/data/telemetry-session02.jsonl`, SHA256 `5815cc268768d2ff34b93734ba74a406d846750e640124a7f00cfadcfdbc5a2a`.

Người dùng chạy logger giới hạn 3600 giây, đã kết thúc và chạy parser. USB được rút sau khi hoàn tất. Kiểm tra này chỉ xử lý file trên máy, không thao tác thiết bị, không sửa raw. Khoảng thời gian có bản ghi không đồng nghĩa chính xác thời gian chạy tiến trình.

| Chỉ số | Kết quả |
| --- | --- |
| Device / calibration | garden-01 / soil-2511-979 |
| Giờ nhận đầu–cuối, Việt Nam | 12:17:45–13:17:15 |
| Giờ đo hợp lệ đầu–cuối, Việt Nam | 12:18:14–13:17:15 |
| Mẫu hợp lệ / trùng / từ chối ở parser | 119 / 0 / 0 |
| Giờ đo / giờ nhận | 118 / 119 mẫu |
| Mẫu thiếu giờ đo | seq 1, clock_ready=false |
| Boot | Một boot: b260ddc8fea8d91f; không thấy reset trong file |
| Sequence | 1 đến 120; thiếu seq 46 |
| Khoảng thiếu | seq 45 lúc 12:39:45 → seq 47 lúc 12:40:45, cách 60 giây |
| Khoảng cách giờ đo | 29–60 giây; trung vị 30 giây |
| Độ ẩm đất | 23,75979–24,86945%; trung vị 24,28198% |
| Nhiệt độ | 32,4–32,7°C |
| Độ ẩm không khí | 57,4–62,6% |
| Ánh sáng raw | 827–3514; chưa quy đổi lux |
| soil_valid / air_valid / tank_ok | True trong cả 119 mẫu |
| pump_on | False trong cả 119 mẫu |
| storage_fault / clock_fault | False trong cả 119 mẫu |
| telemetry_sent | 0; chưa chứng minh nhận/lưu backend |

Một mẫu thiếu không làm toàn phiên vô dụng; giữ khoảng thiếu, không nội suy hoặc tạo seq 46. Không thể xác định nguyên nhân mất mẫu chỉ từ file đã lọc. Con số 1212 dòng malformed/non-JSON do logger báo bao gồm dòng xem nhanh, không phải số mẫu cảm biến mất.

Độ ẩm đầu/cuối cùng khoảng 24,02%, dao động hẹp trong phiên. Chưa có bằng chứng xu hướng khô dài hạn hoặc mức ẩm tuyệt đối; không suy ra nhu cầu tưới chỉ từ số phần trăm này.

## Nhật ký người quan sát

Người dùng xác nhận không tưới thêm, không di chuyển cảm biến và không bấm EN trong phiên. Có mở rồi đóng cửa; không nhớ thời điểm chính xác. Thay đổi ánh sáng được giữ nguyên, không gắn thời gian giả hoặc khẳng định toàn bộ biến động do cửa.

Đã lưu `firmware/data/watering-session02.json`:

- history_complete=true chỉ xác nhận lịch sử trong khoảng quan sát của phiên.
- events rỗng theo xác nhận không tưới trong phiên.
- last_watered_at_before_start=null: đã tưới hôm trước nhưng chưa biết giờ chính xác.
- Sự kiện môi trường mở/đóng cửa có timestamp=null.

## Kết quả chuẩn bị AI

Parser đã có CSV raw, quality report và PostgreSQL staging CSV; xuất file staging không có nghĩa đã nhập PostgreSQL.

Đã chạy builder ra `firmware/data/prepared/telemetry-session02.minutes.csv` và `.minutes.quality.json`, chọn giờ đo, cutoff 13:18 giờ Việt Nam. Có 60 dòng phút; toàn bộ 60 chưa dùng cho AI vì unknown_previous_watering. Phút cuối còn ngoài phạm vi nhật ký đầy đủ. Các lý do có thể chồng nhau.

Đây là cách giữ thiếu của builder, không phải xóa 119 số đo gốc. Dữ liệu raw vẫn dùng để kiểm tra cảm biến và biểu đồ. Model v2 cần minutes_since_water nên không đoán giờ tưới để ép tạo đặc trưng. Phiên một giờ cũng chưa đủ nhiều chu kỳ cho đánh giá thực nghiệm. Không huấn luyện model ở bước này.

## Tiếp theo

1. Giữ nguyên raw và các file đã xuất; không chạy logger nối vào session02.
2. Phiên tiếp dùng tên mới, ghi giờ tưới có thật, lượng nước nếu đo được và các thay đổi môi trường. Không tưới chỉ để tạo nhãn.
3. Thu nhiều chu kỳ tự nhiên, giữ vị trí cảm biến và calibration ổn định.
4. Khi TV2 có API, đối chiếu identity và giờ giữa ESP32 và database rồi mới chốt luồng ESP32 → API → PostgreSQL.

Tài liệu liên quan: [quy trình dữ liệu](WATERING_AND_AI_DATASET.md), [kế hoạch đánh giá AI](REAL_AI_EVALUATION_PLAN.md).
