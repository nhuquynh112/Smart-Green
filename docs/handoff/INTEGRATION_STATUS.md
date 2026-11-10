# TV1 → TV2: trạng thái tích hợp và việc tiếp theo

Cập nhật 10/11/2026. Nhánh chia sẻ: `tv1/firmware-ai-foundation`, đã gộp `tv2/backend-web-integration` tại dadf068. Đây là bản tích hợp đang phát triển, chưa nghiệm thu điều khiển bơm hoặc AI thực nghiệm.

## Đã xác minh trên máy TV1

- ESP32 thật gửi telemetry mỗi khoảng 30 giây, X-API-Key, backend trả HTTP 200; PostgreSQL lưu payload khớp serial.
- Tạm dừng backend 70 giây: ESP32 tiếp tục đọc cảm biến, bơm OFF, tự gửi lại sau khi server phục hồi. Thiếu một mẫu do queue ghi đè; không phải thử ngắt Wi-Fi.
- PostgreSQL 16 và pgAdmin chạy bằng Docker Compose, cổng chỉ bind localhost. Backend chạy trên host để ESP32 gọi qua LAN.
- Chuyển 44 mẫu và 1 thiết bị sang Docker, đối chiếu nội dung cả 5 bảng khớp. Đây là số tại lúc chuyển, không phải số hiện tại.
- Bản bàn giao không chứa Wi-Fi, API key, mật khẩu, database volume, raw log hoặc model local. Báo cáo dẫn tới bằng chứng local, không giả định các artifact đó có trong Git.

## TV2 có thể tiếp tục

1. Kéo/gộp nhánh tích hợp vào nhánh đang làm, làm theo [hướng dẫn máy mới](../LOCAL_DATABASE.md). Dùng cấu hình riêng, không sao chép secret qua Git.
2. Kiểm thử HTTP + PostgreSQL thật: key sai/khác device, telemetry trùng/xung đột, event gửi lại, ACK gửi lại, TTL, sequence sau restart. Test backend hiện dùng SQLite và chủ yếu gọi handler trực tiếp.
3. Đối chiếu web → command → ESP32 → ACK → watering event cùng TV1 khi phần cứng được nghiệm thu. Profile telemetry-only hiện không nhận lệnh, không bật lên chỉ để làm test pass.
4. Kiểm tra xuất CSV/thống kê với dữ liệu thật có timestamp null, khoảng thiếu và tưới tay; phân biệt giờ đo/giờ nhận và ADC ánh sáng/lux.
5. Tích hợp model thật khi TV1 cung cấp bundle và dữ liệu đủ điều kiện. Giữ `can_trigger_pump=false`, không dùng demo synthetic để báo cáo kết quả cây thật.
6. Cập nhật hướng dẫn chạy, backup/restore và bằng chứng test trên máy TV2. Nếu yêu cầu triển khai Internet, cần bổ sung HTTPS và cấu hình triển khai riêng; Compose này chỉ cho local.

## TV1 tiếp tục

Thu dữ liệu thật và nhật ký tưới, kiểm tra cảm biến/phao, đo lưu lượng, nghiệm thu an toàn phần cứng, thử Wi-Fi mất/phục hồi và đánh giá AI với nhiều chu kỳ thật. Không hứa giữ đủ mọi mẫu khi offline: queue hiện tại có giới hạn.

Bằng chứng: [tích hợp ESP32/backend](../ESP32_BACKEND_INTEGRATION_2026-11-09.md). Hợp đồng: [TV2_CONTRACT](../TV2_CONTRACT.md).
