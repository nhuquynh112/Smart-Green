# Rà soát TV2 không dùng phần cứng — 11/11/2026

Board đã bị nước vào: mọi kiểm thử trong đợt này chạy trên máy tính với dữ liệu mô phỏng. Không nạp firmware, không gửi lệnh điều khiển, không khởi động lại backend đang nối thiết bị.

## Thay đổi

- Dashboard OFF không còn hiển thị cooldown của chế độ tự động như thời gian phải chờ trước khi tưới thủ công. MANUAL vẫn tuân theo cooldown mà thiết bị báo; ACK đổi chế độ chưa thay thế telemetry mới để mở nút tưới.
- Lịch sử ghi rõ đây là thời lượng firmware ghi nhận. ACK bật/tắt đầu ra không chứng minh motor hoặc dòng nước đã dừng. Lý do Tank được dịch thành dừng do phao báo thiếu nước.
- Biểu đồ dùng trục thời gian thực; khoảng trống trên 90 giây ngắt đường, không nội suy qua nhiều giờ mất dữ liệu. Dự báo chỉ hiện ở khối AI, không trộn vào mẫu đo.
- Escape nội dung từ thiết bị, lệnh và lịch sử trước khi đưa vào HTML.
- API trả null cho lượng nước và lưu lượng nếu chưa cấu hình hiệu chuẩn hợp lệ, thay vì mặc định 10 ml/s. Dashboard tiếp tục ghi “Chưa hiệu chuẩn”.
- Sao lưu PostgreSQL yêu cầu REPEATABLE READ READ ONLY trước khi đọc các bảng, tránh lấy dữ liệu từ nhiều thời điểm khác nhau trong cùng bản sao lưu.

## Kiểm thử

- `node backend/tests/dashboard_controls.test.cjs`: 9 trường hợp, gồm cập nhật chế độ, chống gửi trùng, ACK/hết hạn, cooldown, quota, khoảng trống biểu đồ và escape HTML.
- `.venv-ai/bin/python -m pytest backend/tests/test_api.py -q`: bộ kiểm thử API với SQLite cô lập; có kiểm thử đi qua ASGI cho xác thực, hạn mức và STOP. Kiểm thử PostgreSQL snapshot dùng mock để kiểm tra thứ tự thiết lập transaction, chưa xác nhận cạnh tranh trên PostgreSQL thật.
- `bash tools/test_firmware.sh`: mô phỏng native controller, ranh giới an toàn, runtime, profile và timestamp. Không phải kiểm thử relay thật.

## Còn cần kiểm tra sau

- Kiểm tra board/relay và nguồn sau sự cố nước trước khi cấp điện. Hiện tượng OFF nhưng bơm còn chạy chưa được xác định nguyên nhân.
- Đo thời gian motor và lượng nước độc lập; số 175 ml trước đây chưa đủ tin cậy để hiệu chuẩn.
- Kiểm tra tích hợp PostgreSQL và nhiều yêu cầu đồng thời trong môi trường thử riêng.
- Kiểm tra giao diện trực quan trên trình duyệt; bộ Node hiện kiểm tra logic với DOM mô phỏng.
- Sau khi triển khai phần mềm: Python backend cần khởi động lại, trang web cần tải lại. Đợt này chưa triển khai vào tiến trình đang chạy.

## MANUAL không giới hạn số lần — cập nhật theo yêu cầu

Runtime dùng `manualUnlimitedStarts=true`: bỏ kiểm tra số lần cho lệnh Manual, vẫn ghi nhận mọi lần chạy và giữ hạn mức thời gian tổng, max pulse, phao, cảm biến, clock và event queue. AUTO giữ giới hạn số lần. Telemetry `quota_limit_starts=0` biểu thị không giới hạn số lần trong MANUAL; backend/dashboard đã hỗ trợ sentinel này. Firmware cũ vẫn có hạn mức như trước cho đến khi được nạp bản mới. Không xóa NVS hoặc đặt lại số liệu. Cấu hình local hiện tổng 20 giây/cửa sổ 24 giờ, tối đa 1 giây/lần. Điều này không đồng nghĩa tưới vô hạn về tổng thời gian.

Kiểm thử bổ sung: native vượt số lần trong MANUAL nhưng vẫn chặn tổng thời gian và AUTO; 2 API tests cho count=0 và hết time budget; dashboard tổng 11 ca.
