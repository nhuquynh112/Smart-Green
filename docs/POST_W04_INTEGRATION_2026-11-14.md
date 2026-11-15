# Ghép bản sửa đã chuẩn bị trong lúc thu W04

Ngày 14/11/2026: đã áp dụng `artifacts/w04-safe-review/after-w04.patch` lên working tree sau commit W04 `257545a`, giữ các sửa offline trước đó. Patch kiểm tra được trước khi áp dụng, không xung đột. Không áp dụng lại patch này lần nữa.

## Nội dung

- Dashboard có hướng dẫn riêng OFF/MANUAL/AUTO, chỉ nhập thời lượng trong MANUAL; STOP luôn hiện. Thông tin mô hình và chân trời dự báo lấy từ kết quả thực, có nhãn dữ liệu cũ.
- Nhật ký phiên có lưu, sửa theo revision và xuất ZIP. Chỉ quản trị được truy cập, mỗi thiết bị tối đa một phiên đang mở, gửi lại yêu cầu sau mất phản hồi không tạo revision trùng.
- Nhật ký ghi sự kiện tưới, lượng thực đo nếu biết, khoảng lịch sử không rõ; không tạo lệnh bơm từ sự kiện nhập tay.
- Backup JSON gồm cả `collection_sessions` và `collection_session_revisions` cùng năm bảng trước đó. Backup PostgreSQL đọc cùng một snapshot repeatable read.
- AI dữ liệu thật cần đối soát riêng cho từng lần dự báo, gắn mốc thời gian và boot; không dùng lại checkbox cũ hoặc dữ liệu đến sau mốc đối soát. AI vẫn không có quyền bật bơm.

## Phạm vi triển khai

Đã ghép mã nguồn, **chưa restart backend, chưa nạp firmware, chưa thay đổi database đang thu**. HTML là file tĩnh nên có thể hiện giao diện mới khi tải lại trang dù tiến trình backend vẫn chạy code cũ; các nút nhật ký cần backend khởi động lại mới dùng được.

Ngoài phiên thu, lưu backup hiện trạng trước khi khởi động backend mới theo quy trình vận hành hiện tại. Khi khởi động, backend bổ sung hai bảng/index, không xóa dữ liệu cũ. Không cần nạp lại ESP32 cho các thay đổi này. Thử tạo/sửa/kết thúc/xuất một phiên thử trước khi dùng cho phiên thực tiếp theo.

Backup W04 đã commit riêng là sao lưu dữ liệu phiên, không thay thế backup toàn bộ database. Không đưa backup DB đầy đủ chứa thông tin xác thực thiết bị lên Git công khai.

## Giới hạn

Nhật ký phiên hiện phục vụ xuất dữ liệu và xử lý AI offline, chưa thay thế nguồn `watering_events` của AI online. Không được hiểu rằng nhập nhật ký là AI online tự có đủ lịch sử. Khung export phiên mới là `[start,end)` theo giờ nhận; W04 bàn giao dùng hai đầu bao gồm, đã được xử lý riêng trong bằng chứng W04.

Chưa nghiệm thu giao diện bằng trình duyệt thật hoặc phần cứng. Không thay đổi các gói dữ liệu/mô hình W01–W04.

## Kiểm chứng sau ghép

- Backend API/AI/nhật ký: 93 passed, 4 PostgreSQL variants skipped trong lượt SQLite.
- Lượt riêng trên PostgreSQL 16 tạm UTF-8 (Unix socket, không phải database thật): 10 passed, gồm test SQLite/PG nhật ký và chống lặp lệnh; có trùng với bộ trên nên không cộng thành tổng độc lập.
- Dashboard Node: 20 passed.
- `verify_evidence.py`: toàn bộ manifest W01–W04 và MAE/checksum candidate đạt; `git diff --check` sạch.
- Cụm PostgreSQL thử nghiệm đã dừng sau kiểm tra. Lượt đầu dùng cụm tạm cũ thất bại do sai tên role, sau đó tạo cụm mới có role tường minh và chạy đạt; không có sửa production DB để khắc phục lỗi môi trường test.
