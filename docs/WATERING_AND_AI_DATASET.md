# TV1 — Nhật ký tưới và CSV AI v2

Công cụ chỉ xử lý file trên máy tính; không mở Serial, gửi lệnh thiết bị hoặc kết nối database.

## 1. Ghi nhật ký phiên quan sát

Chạy từ thư mục gốc repository. Các ngày/ID bên dưới là ví dụ, thay bằng phiên thực tế. Không chạy nguyên ví dụ rồi coi là số đo.

```bash
python tools/watering_journal.py init firmware/data/watering-session01.json \
  --device-id garden-01 --calibration-id soil-2511-979 \
  --start '2026-11-08T08:00:00+07:00' --end '2026-11-08T20:00:00+07:00'
```

Lệnh tạo file mới, không ghi đè file cũ. `history_complete=false` mặc định: chưa xác nhận lịch sử tưới đầy đủ. `last_watered_at_before_start=null` nghĩa chưa biết lần tưới gần nhất trước phiên.

Sau mỗi lần tưới, ghi thời điểm thực tế bắt đầu/kết thúc; lượng nước chỉ điền nếu đo được:

```bash
python tools/watering_journal.py add firmware/data/watering-session01.json \
  --event-id hand-001 --method hand \
  --start '2026-11-08T10:00:00+07:00' --end '2026-11-08T10:00:30+07:00' \
  --volume-ml 20 --note 'Ví dụ cú pháp, thay bằng số đo thật'
```

Không biết ml thì bỏ `--volume-ml`. Tưới tay không nhận `--actual-ms`; tuyệt đối không suy ra thời gian bơm. Với bơm, `--method pump --actual-ms ...` chỉ ghi khi biết thời gian thực tế; null được giữ nếu không biết.

Kết thúc phiên, sửa file JSON:

- Đặt `coverage_start/end` đúng khoảng quan sát, không xác nhận trước cho tương lai.
- Điền `last_watered_at_before_start` với múi giờ nếu biết chính xác lần tưới kết thúc trước phiên; không biết giữ null.
- Ghi các khoảng không biết lịch sử trong `unknown_intervals`, ví dụ `[{"start":"2026-11-08T12:00:00+07:00","end":"2026-11-08T13:00:00+07:00"}]`.
- Chỉ đặt `history_complete=true` sau khi đối chiếu nhật ký. Cờ này là xác nhận của người quan sát, phần mềm không tự xác minh được.

```bash
python tools/watering_journal.py check firmware/data/watering-session01.json
```

## 2. Tạo lưới phút cho AI

```bash
python tools/build_ai_dataset.py firmware/data/session01.jsonl \
  --journal firmware/data/watering-session01.json \
  --as-of '2026-11-08T20:00:00+07:00' \
  --output firmware/data/ai/session01.csv
```

Mặc định dùng giờ đo `timestamp`. Bản bringup có timestamp=null nên lệnh sẽ từ chối nếu không có mẫu nào có giờ đo. Với dữ liệu mới thu qua logger, có thể chủ động thêm:

```text
--time-basis received_at_proxy
```

Tùy chọn này dùng `received_at` làm trục thời gian thay thế, giữ `time_basis=received_at_proxy` trong CSV và báo cáo. Đây là thỏa hiệp cho phiên bench, không đổi ý nghĩa log gốc và không chứng minh thời gian đo chính xác. Kiểm tra đồng hồ laptop, độ trễ/buffer và reset trước khi dùng đánh giá thực tế. Không trộn tập proxy với tập giờ đo; mô hình và dữ liệu dự đoán phải cùng time_basis. Log cũ thiếu cả hai loại giờ không thể phục hồi bằng công cụ này.

Đầu ra: CSV và `.quality.json` chứa thống kê, nguyên nhân loại và SHA256 file nguồn. Có thể truyền nhiều file JSONL theo thứ tự thu. Các file phải cùng device, calibration và data_origin với nhật ký. Xung đột cùng identity sẽ chặn tạo dataset.

## 3. Cách tổng hợp và loại dữ liệu

- Chỉ lấy phút UTC đã hoàn tất trước `--as-of`; timestamp là đầu phút, dữ liệu chỉ sẵn sàng sau cuối phút.
- Median trong phút; nếu một mẫu cảm biến báo invalid, toàn bộ giá trị cảm biến đó trong phút bị để trống.
- Không nội suy hay forward-fill. Không có mẫu thì giữ phút trống.
- Phút có bơm chạy, có sự kiện tưới, đổi boot hoặc trộn hai boot bị loại. Khoảng lịch sử/tương lai của AI chạm phút trống cũng bị loại.
- Ngoài khoảng nhật ký, chưa duyệt lịch sử hoặc chưa biết lần tưới trước thì không tạo đặc trưng hợp lệ.
- Khi có khoảng lịch sử không rõ, phần còn lại của phiên bị loại bảo thủ. Tạo nhật ký/CSV riêng từ một lần tưới đã biết để bắt đầu phiên mới; không nối bộ đếm đã reset.
- `water_event_count` đếm sự kiện tưới hoàn tất trong phiên, dùng chung cho tưới tay và bơm. Không phải lượng nước hay thời gian bơm.
- `minutes_since_water` tính ở cuối phút từ lần tưới kết thúc gần nhất. Sự kiện có khoảng thời gian chồng nhau phải được đối chiếu trước.

Công cụ chưa nhận nhật ký sự kiện backend tự động: TV2 cần ánh xạ event vào schema nhật ký. Event `Reboot` hoặc thời điểm không chắc chắn phải tạo khoảng không rõ, không giả thời gian.

## 4. Kiểm tra rồi huấn luyện

```bash
python -m smart_green_ai.assess firmware/data/ai/session01.csv --output artifacts/session01-readiness.json
python -m smart_green_ai.train firmware/data/ai/session01.csv --horizon 30 --output artifacts/session01-model
```

Chỉ chạy train sau khi xem blockers, tỷ lệ dữ liệu thiếu và số chu kỳ thực tế. `training_pipeline_ready=true` chỉ xác nhận điều kiện kỹ thuật, không chứng minh đủ dữ liệu khoa học.

## 5. Thay đổi phiên bản AI

`feature_version=v2-watering-events` thay `water_total_ms` bắt buộc bằng `water_event_count`. CSV/model v1 phải tạo lại từ dữ liệu và nhật ký gốc rồi huấn luyện lại; không đổi tên cột milliseconds thành event count. Simulator đã xuất schema v2. Metadata ghi time_basis; inference từ chối model v1, sai calibration/origin/time_basis, phút chưa hoàn tất hoặc dữ liệu cũ hơn 120 giây tính từ cuối phút.

Model vẫn chỉ trả đề xuất và `can_trigger_pump=false`.
