# Phản hồi điều khiển và thời gian nghỉ

## Thay đổi

- Dashboard giữ lựa chọn chế độ, chặn gửi lặp khi lệnh đang chờ và hiển thị ACK hoặc hết hạn. STOP không bị khóa bởi hàng đợi giao diện.
- ACK đổi chế độ mới hơn telemetry được hiển thị ngay, chỉ khi thời điểm lệnh thuộc phiên khởi động hiện tại. Telemetry vẫn là nguồn trạng thái định kỳ.
- ESP32 bỏ đọc body cho HTTP 204. HTTPClient trước đó có thể chờ kết nối keep-alive đóng khi response không có Content-Length, làm chậm polling/ACK.
- Chu kỳ polling lệnh giảm từ 2 giây xuống 1 giây; độ trễ thực tế còn phụ thuộc Wi-Fi và HTTP.
- ESP32 gửi telemetry khi chế độ, trạng thái bơm hoặc số lệnh xử lý thay đổi. Payload có control_revision=responsive-controls-v2 và cooldown_remaining_ms.
- Dashboard khóa tưới khi đang nghỉ, offline, chưa MANUAL, phao/cảm biến không đạt hoặc còn lệnh chờ. Đếm ngược theo dữ liệu ESP32, bắt đầu từ thời điểm server nhận để không mở khóa sớm do thời gian truyền.

## Giới hạn giữ nguyên

Theo yêu cầu người dùng, MANUAL không có thời gian nghỉ (SG_MANUAL_COOLDOWN_MS=0); AUTO giữ 600000 ms (10 phút). MANUAL có thể gửi lần tưới mới sau khi lần trước kết thúc và đủ điều kiện, kể cả sau khởi động. AUTO vẫn áp dụng khoảng nghỉ sau khởi động và khi dừng bơm. Giữ giới hạn xung, hạn mức ngày và khóa phao. Lệnh bị từ chối vì cooldown không tự chạy lại sau đó.

## Áp dụng

Tải lại trình duyệt để nhận HTML mới; không cần restart backend cho thay đổi static. Firmware cần nạp lại qua USB khi adapter bơm đã rút và Serial Monitor đã đóng. Sau nạp, kiểm tra payload có control_revision mới và dashboard có đếm ngược. Chỉ thử bơm có giám sát khi hết thời gian nghỉ, phao đủ nước và trạng thái MANUAL đã được xác nhận.

## Kiểm tra

- `node backend/tests/dashboard_controls.test.cjs`: giữ lựa chọn, chặn lệnh lặp, ACK từ chối, hết hạn, cooldown, ACK chế độ và loại ACK trước reboot.
- Native controller: cooldown còn lại và vòng lại bộ đếm millis.
- Build PlatformIO esp32dev.

Chưa đo độ trễ thực tế trên phần cứng sau khi nạp bản này. Không gửi lệnh chạy bơm trong kiểm tra phần mềm.
