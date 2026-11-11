# Rà soát mã trước phiên thu tiếp — 11/11/2026

## Phạm vi

Rà controller, adapter GPIO/timer, vòng lặp firmware, giao thức/mạng, endpoint tạo lệnh, trạng thái dashboard và pipeline tạo đặc trưng AI. Sửa trên workspace đang có thay đổi từ các lượt trước; không reset mã, không sửa dữ liệu thu, không nạp firmware, không restart backend, không gửi lệnh tới thiết bị.

## Lỗi đã sửa trong lượt này

1. **Thời lượng xung tính cả thời gian ghi flash.** Controller lưu mốc ms lấy trước khi persist, trong khi GPIO chỉ bật sau persist. Tick có thể tắt sớm, phù hợp dấu hiệu xung 500 ms chỉ ghi khoảng 460 ms. PumpOutput nay cung cấp mốc bật vật lý; controller dùng mốc đó. Main lấy lại millis trước tick để tránh trừ unsigned khi tick cũ hơn mốc bật. Test mô phỏng chậm 40 ms chứng minh xung vẫn đủ 500 ms. Không đồng nghĩa đã đo được motor thật; vẫn có độ trễ lịch task và guard.
2. **Lỗi refresh để nguyên nút WATER sẵn sàng.** Dashboard nay khóa WATER khi refresh thất bại; chỉ mở lại sau lần tải trạng thái thành công. Thông báo lỗi refresh tự hết sau khôi phục, không xóa thông báo khác.
3. **Đổi thiết bị dùng trạng thái cũ.** Khóa nút ngay khi đổi, không cho gửi WATER/SET_MODE nếu dashboard chưa thuộc thiết bị đã chọn; tải tiếp thiết bị mới sau request cũ kết thúc.
4. **Lệnh chứa trường của loại khác.** Ví dụ SET_MODE kèm duration_ms trước đây có thể chạm constraint PostgreSQL và lỗi 500. API nay từ chối 400 trước ghi DB; STOP/WATER/SET_MODE chỉ nhận trường đúng loại.
5. Bỏ escape HTML thừa trong thông báo textContent của ACK chế độ.

## Kiểm chứng

- Python backend + AI + tools: **97 passed, 8 subtests passed**.
- Dashboard DOM mô phỏng: **13 passed**.
- Native firmware: controller, safety boundaries, runtime, profiles và telemetry đều qua.
- ESP32: build riêng, không upload; kết quả build được ghi trong phản hồi của lượt này.
- `git diff --check`: không có lỗi whitespace.

## Giới hạn và việc chưa xác nhận

- Chưa kiểm thử trình duyệt trực quan và PostgreSQL concurrent requests trên database thử riêng trong lượt này. SQLite/ASGI tests không thay thế việc đó.
- AUTO và MANUAL vẫn dùng chung bộ đếm/window trong NVS; manual không giới hạn số lần nhưng vẫn tiêu hao thời gian và tăng số lần khiến AUTO có thể hết quota. Đây là chính sách hiện tại, chưa tách bộ đếm vì cần migration NVS và quyết định ngân sách riêng. Không xóa NVS để vượt hạn mức.
- Một request mạng chưa trả về vẫn có thể giữ UI ở trạng thái chờ; chưa bổ sung timeout và đối soát trạng thái lệnh khi response bị mất. Backend/firmware tiếp tục kiểm tra dữ liệu cũ, hạn lệnh và giới hạn xung.
- Thử thật thời lượng motor, phao và STOP khi đang chạy vẫn cần thực hiện sau khi kết thúc phiên thu, ngắt nguồn tải trong lúc nạp.
- Các số 30–35 ml/lần chỉ là ước lượng người dùng; chưa cài làm hiệu chuẩn. Pipeline AI đạt kiểm tra kỹ thuật không chứng minh đủ chu kỳ độc lập.

## Áp dụng sau phiên thu

Chỉ sau khi chốt log: nạp firmware mới với adapter bơm ngắt; restart backend; tải lại giao diện. Sau đó kiểm tra xung có giám sát và đối chiếu event với thời gian quan sát. Không cần thay đổi schema DB/NVS cho các sửa đổi trong lượt này.

## Áp dụng thực tế sau rà soát

Ngày 11/11/2026, sau khi người dùng xác nhận ngắt nguồn tải và cắm USB: upload `esp32dev` qua `/dev/ttyUSB0` thành công, hash flash được xác minh; restart backend thành công. Mẫu đo lúc 21:38:04 giờ Việt Nam: sample_seq=2, OFF, pump_running=false, clock_ready=true, clock_fault=false, storage_fault=false, tank_ok=true, server_available=true. Chưa phát lệnh bơm thử; kiểm thử phần cứng để buổi sau.
