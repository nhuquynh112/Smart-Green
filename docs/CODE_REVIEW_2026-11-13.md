# Rà soát logic offline — 13/11/2026

Phạm vi: đường chuẩn bị dữ liệu AI online so với builder offline; kiểm tra đầu vào telemetry; đọc lại các chốt WATER/STOP, quota và thực thi firmware. Không phải chứng nhận toàn bộ hệ thống không còn lỗi.

## Lỗi đã sửa

1. **Phút chưa kết thúc làm gián đoạn dự báo online.** Dịch vụ AI trước đây đưa cả phút đang ghi vào dataframe, trong khi inference yêu cầu phút đã đóng. Nay chỉ lấy mẫu trước đầu phút hiện tại; không thay thời gian mẫu hoặc điền dữ liệu thiếu.
2. **Dữ liệu đang tưới có thể đi vào đặc trưng dự báo không tưới.** Online trước đây không loại phút có pump_running và chỉ tăng bộ đếm sau khi sự kiện tưới kết thúc. Với lần tưới dài, phần giữa vẫn có thể được coi là lịch sử không tưới. Nay vô hiệu hóa phút có mẫu bơm chạy và mọi phút giao với khoảng tưới, bao gồm phút kết thúc, tương tự builder offline. Khoảng sự kiện kết thúc trước bắt đầu bị từ chối. Phải đủ lại 16 phút liên tiếp hợp lệ mới dự báo được.
3. **Cờ an toàn chưa được kiểm tra kiểu trước lưu.** commissioned/storage_fault/clock_ready/clock_fault/server_available trước đây chấp nhận giá trị không phải boolean. Chuỗi có thể gây lỗi lưu PostgreSQL hoặc bị diễn giải sai khi kiểm tra truthiness. Nay giá trị có mặt phải là boolean JSON; sai kiểu trả 422 trước khi ghi. Trường không có vẫn giữ tương thích như trước.

## Kiểm thử

- 5 ca hồi quy AI: phút chưa đóng, một mẫu bơm trong phút, sự kiện tưới dài, biên phút kết thúc và phục hồi, khoảng thời gian đảo ngược.
- 25 tổ hợp cờ an toàn sai kiểu, xác nhận từ chối và không ghi telemetry.
- AI service + pipeline AI + builder dataset: 42 ca đạt. Backend API + AI service: 87 ca đạt (bao gồm 25 tổ hợp cờ sai kiểu và 5 ca AI, không cộng các bộ có ca trùng).
- Lượt backend trong sandbox bị treo tại nhóm ASGI và đã dừng; chạy lại ngoài sandbox với DATABASE_URL=sqlite:///:memory: đạt 87/87, không dùng database thật.
- Kiểm thử firmware native: controller, safety boundaries (6 nhóm), runtime, profiles và telemetry time đều đạt. Đây là mô phỏng trên máy tính, không phải nghiệm thu bơm thật.

## Triển khai và giới hạn

Không restart backend, không truy cập database thu dữ liệu, không nạp firmware hoặc gửi lệnh thiết bị. Launcher backend/run_local.py không bật auto-reload. Thay đổi chỉ áp dụng khi khởi động lại backend sau phiên thu; không cần nạp ESP32 cho bản sửa này.

Không sửa dữ liệu/mô hình W01–W03. AI vẫn chỉ trả khuyến nghị, can_trigger_pump=false. Không đổi hạn mức hay bỏ chốt bảo vệ. Còn cần nghiệm thu phần cứng trên phiên bản đang dùng, kiểm tra phao dao động, đo lưu lượng, đối chiếu lịch sử tưới tay và đánh giá nhiều chu kỳ. Không thay đổi giữa W04 để tránh làm nhiễu phiên thu.
