# Rà soát tiếp — 12/11/2026

Điểm xuất phát: commit d3f43ff trên nhánh tv1/firmware-ai-foundation; workspace sạch, local tracking origin cùng commit. Không fetch remote trong lượt này.

## Đã sửa

- Request dashboard/API có timeout 10 giây, bao gồm đọc JSON; giải phóng cờ refresh để lần poll tiếp theo phục hồi.
- Khi POST mất phản hồi, không xem đó là chắc chắn chưa tạo lệnh. Khóa gửi WATER/SET_MODE tiếp trong trang hiện tại, hiển thị hướng dẫn STOP; không tự retry POST, không đoán command ID từ lệnh có cùng nội dung của client khác.
- STOP vẫn gửi được khi một lệnh đang chờ. Token theo request ngăn phản hồi WATER cũ ghi đè phản hồi hoặc trạng thái theo dõi STOP mới. Sau phản hồi STOP có mã lệnh hợp lệ, tiếp tục chờ ACK theo cơ chế hiện có.
- kind/mode không phải chuỗi bị trả 400 trước khi kiểm tra tập giá trị; list/dict không còn gây TypeError/500.

## Cơ chế hoàn thiện

### Hạn mức độc lập

Runtime bật `separateManualQuota`: AUTO (RULE/AI) giữ ngân sách cũ; MANUAL có cửa sổ 24 giờ, thời gian dự trù và bộ đếm riêng. Cả hai ngân sách dùng mức `SG_DAY_MS` cấu hình hiện tại, tức tổng ngân sách cho hai chế độ có thể bằng hai lần mức đó; đây là hai ngân sách riêng, không phải hạn mức tổng toàn hệ thống. MANUAL vẫn không giới hạn số lần; mỗi xung, tổng thời gian, phao, cảm biến và thời gian hợp lệ vẫn được kiểm tra. Thời gian nghỉ AUTO vẫn tính sau lần bơm gần nhất để tránh tưới nối tiếp quá sát.

State NVS đổi sang magic v2 và thêm bộ đếm MANUAL. Loader nhận dạng chính xác kích thước v1/v2. Migration v1 giữ ID lệnh/sự kiện và nhật ký chưa ACK, chuyển OFF; do không thể phân loại các sự kiện đã ACK khỏi bộ đếm chung, phần sử dụng cũ được giữ trong CẢ HAI ngân sách đến hết cửa sổ cũ. Không xóa NVS, không tự hoàn quota. Lỗi đọc/lưu migration khóa điều khiển. Firmware cũ thấy kích thước v2 không hợp lệ và khóa thay vì coi là state trắng; không rollback tùy tiện.

Telemetry `control_revision=separate-quota-v5`, `quota_policy=separate-v2`, `quota_scope=MANUAL|AUTO`; các trường quota hiện có mô tả ngân sách của chế độ hiện tại (OFF hiển thị AUTO). Giao diện ghi rõ tên ngân sách.

### Chống lệnh trùng bền vững và chặn lệnh cũ sau STOP

- `commands` thêm `request_id`, `request_fingerprint` và unique index `(device_id,request_id)` khi ID không NULL; migration bổ sung cột, không xóa dữ liệu cũ.
- WATER và SET_MODE bật chế độ bắt buộc có request_id 16–80 ký tự cùng expected_seq (số thứ tự cao nhất đã thấy). Trang cũ thiếu các trường này bị từ chối và yêu cầu tải lại. STOP/SET_MODE OFF không có ID vẫn được phép để giữ khả năng dừng từ trang cũ.
- Trong cùng transaction, khóa dòng device rồi đối soát request trước kiểm tra telemetry. Cùng ID/nội dung trả đúng lệnh cũ HTTP 200, không cấp seq/hạn mới; ID đổi nội dung trả 409.
- Yêu cầu mới chỉ tạo nếu expected_seq khớp watermark server. Hai tab cùng trạng thái cũ dù dùng ID khác nhau chỉ một yêu cầu được nhận. STOP không bị fence cản, nhưng tăng seq để chặn WATER cũ đến sau nó.
- Dashboard lưu yêu cầu vào localStorage trước gửi, phục hồi qua reload/tab khác, chỉ đối soát bằng request_id chính xác. Nếu request đã rơi khỏi 30 lệnh dashboard thì GET `/api/v1/web/devices/{device_id}/requests/{request_id}` tìm trực tiếp. Không tự retry POST; chưa tìm thấy yêu cầu vẫn khóa tưới mới và cho phép STOP.
- SQLite dùng RLock cho connection dùng chung; PostgreSQL dùng khóa dòng device và unique index. Kiểm thử PostgreSQL tạo/xóa database ngẫu nhiên `sg_test_*` riêng, không chạm dữ liệu thu.

Việc mở tab với trạng thái mới rồi chủ động bấm tưới lần nữa là yêu cầu mới hợp lệ; không coi mọi lần bấm giống nhau là lệnh trùng.

### Triển khai

Chưa restart dịch vụ hay nạp phần cứng trong lượt sửa này. Sau phiên thu: sao lưu DB và cấu hình; restart backend để chạy migration bổ sung cột; nạp firmware khi adapter bơm ngắt; Ctrl+Shift+R các tab; xác nhận revision, OFF, đồng hồ và quota_scope trước test có giám sát. HTML trên đĩa thay đổi có thể được server hiện tại phục vụ khi reload, nên tránh điều khiển bằng trang mới trước khi backend đã restart. Dữ liệu thu không bị sửa.

### Kết quả kiểm chứng cuối của hai mục

- Toàn bộ backend + AI + tools: 112 passed, 8 subtests passed trước khi bổ sung ca mở lại SQLite.
- Sau bổ sung ca mở lại SQLite và thử migration PostgreSQL từ bảng commands cũ: backend test_api + PostgreSQL: 58 passed.
- Dashboard: 19 passed, gồm reload/tab khác, đối soát đúng request ID, STOP ở tab khác giải phóng trạng thái chờ.
- Native firmware: tất cả bộ test đạt; có ca tách ngân sách, reboot/ACK, migration và hết hạn từng ngân sách riêng.
- PlatformIO esp32dev build SUCCESS, flash 960901 byte, RAM 47620 byte; không upload.
- git diff --check đạt. Chưa có kiểm chứng vật lý trên bản separate-quota-v5.

### Kiểm tra trước push trong lúc thu W02

- `env -u SG_TEST_POSTGRES_ADMIN_URL DATABASE_URL=sqlite:///:memory: .venv-ai/bin/python -m pytest backend/tests -q`: 57 passed, 1 skipped (PostgreSQL opt-in).
- `node --test backend/tests/dashboard_controls.test.cjs`: đạt.
- `.venv` thiếu FastAPI; dùng `.venv-ai` sẵn có, không cài thêm dependency. Ca ASGI bị treo trong sandbox đã dừng và chạy lại ngoài sandbox với SQLite trong RAM, đạt như trên.
- Không kết nối database thu, không restart dịch vụ hoặc upload thiết bị. Các kết quả PostgreSQL/phần cứng ở mục trước là bằng chứng lịch sử, không phải chạy lại trong phiên này.
