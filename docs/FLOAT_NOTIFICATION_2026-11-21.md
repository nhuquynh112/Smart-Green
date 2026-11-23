# Thông báo phao — 21/11/2026

Đã sửa source, chưa upload; W07 tiếp tục dùng firmware đã nạp khoảng 12:09.

- FloatTelemetry chỉ quyết định thời điểm phát telemetry; không dùng giá trị chống rung để điều khiển bơm.
- Đổi trạng thái ổn định 250ms và cách lần publish trước ít nhất 1000ms thì yêu cầu publish. Đổi ngược về giá trị đã báo thì hủy thông báo chờ. Publish định kỳ/đổi điều khiển vẫn có thể báo trạng thái raw ngay.
- Không trì hoãn lịch telemetry định kỳ 30 giây khi có thông báo thêm. Thông báo dùng hàng đợi telemetry hiện có; không đảm bảo lưu mọi cạnh phao khi mất mạng.
- Bảo vệ phao GPIO/guard/controller giữ nguyên. Không sửa Dashboard, DB hoặc phiên thu.
- Có thêm bản ghi telemetry khi trạng thái thay đổi, mang thời gian mẫu cảm biến gần nhất như publish điều khiển hiện có; không gọi đó là lần đo đất mới. Khi phân tích phiên, xử lý bằng pipeline phút hiện có và kiểm tra timestamp lặp.

Native suite PASS, AUTO audit 36 PASS; test mới bao gồm debounce, bounce, rate limit, trạng thái không đổi, publish thường và millis rollover. Build esp32dev SUCCESS; không upload.

Sau khi W07 kết thúc, nạp có giám sát với nguồn bơm ngắt. Quan sát đổi phao hai chiều; đối chiếu Serial/API/UI và nhịp định kỳ, không thử an toàn motor bằng riêng thông báo Dashboard. Mục tiêu thông báo nhanh hơn 30s, không cam kết độ trễ thời gian thực; còn network worker và UI polling 2s. Ghi giờ/phiên bản khi nạp.
