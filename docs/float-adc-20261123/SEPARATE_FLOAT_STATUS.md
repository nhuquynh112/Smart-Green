# Trạng thái phao riêng — 23/11/2026

## Bản sửa

Phao ổn định 250ms, cách lần báo trước ít nhất 1s: enqueue FloatPacket độc lập chỉ có boot_id, uptime_ms, observed_at, tank_ok. Gửi POST /api/v1/devices/{id}/float-status có X-API-Key, queue latest-only và retry có hạn tuổi 60s. Không thêm sample_seq và không gọi publish telemetry từ cạnh phao. Telemetry thường và báo thay đổi điều khiển giữ nguyên. Guard phao vẫn đọc trực tiếp GPIO.

Backend tạo bảng float_status khi khởi động bản mới; chỉ một trạng thái hiện tại mỗi thiết bị, không tạo telemetry hoặc sửa raw. Kiểm tra khóa, boot mới nhất, tuổi gói 90s, giá trị kiểu chặt và thứ tự uptime (có rollover). Retry cùng uptime không gia hạn độ mới. Bảng này là trạng thái hiện tại, không phải nhật ký bơm hoặc lịch sử mọi cạnh phao.

Dashboard chọn thông báo cùng boot, mới hơn mẫu thường, tuổi <=90s; nếu không thì dùng phao trong telemetry. Độ mới phao và đất độc lập: thông báo phao không làm mới nhãn cảm biến đất. Giữ polling UI 2s. Thời gian hiển thị phụ thuộc Wi-Fi, hàng đợi và vòng worker 1s; chưa cam kết độ trễ trên board.

Không tự thay giới hạn ADC/hiệu chuẩn; raw52/122 vẫn clamp100 theo công thức cũ. Không gọi nhãn valid là chứng nhận độ ẩm vật lý. Nguyên nhân spike chưa xác minh; tách gói vẫn tăng hoạt động mạng nên cần test A/B, không tuyên bố đã hết nhiễu.

## Triển khai có thứ tự

Source đã sửa; chưa restart backend hoặc upload. Khi ngoài phiên thu:
1. Giữ bơm ngắt và mode OFF; đóng Monitor trước upload.
2. Restart backend bằng launcher local để route/bảng mới sẵn sàng (tạo bảng phụ, giữ telemetry/session cũ); Ctrl+Shift+R Dashboard.
3. Nạp env esp32dev; mở Monitor115200, chờ đồng bộ.
4. Giữ dây/đầu dò cố định; phao yên60s, nâng10s/hạ10s x3. So soil_raw trên Serial trước/trong/sau và đo trễ phao trên UI. Kiểm tra không có reset và không tăng mẫu đất theo cạnh phao.
5. Nếu raw tụt0/nhảy100, dừng kết luận và lưu log; không che bằng lọc. Có thể dùng bản đối chứng trước đó để đối chiếu. Chưa bật AUTO/AI.

## Kiểm thử

Test API: auth, payload, boot, gói cũ/trùng, không chạm telemetry. Test UI: phao mới và đất cũ, fallback khi thông báo quá hạn/boot cũ. Native: debounce, chống rung, giới hạn nhịp/rollover. Regression AUTO/firmware và build esp32dev có bằng chứng tại evidence-separate/.

## Xác nhận người dùng 23/11/2026

Người dùng đã thực hiện hướng dẫn restart/nạp/test và báo “ok ổn rồi”, yêu cầu push bản này. Đây là nghiệm thu quan sát do người dùng báo; chưa có phép đo định lượng độ trễ/ADC hoặc chứng minh nguyên nhân vật lý. Các thông số test phần mềm: 202 Python PASS, 8 SKIP, 8 subtests PASS; 31 UI PASS; 36 AUTO PASS; native/build SUCCESS. Trạng thái “chưa nạp” bên trên là mốc trước bàn giao, không phải trạng thái sau xác nhận này.
