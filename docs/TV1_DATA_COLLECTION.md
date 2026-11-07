# TV1 — Thu và kiểm tra dữ liệu cảm biến

Cập nhật 07/11/2026. Chạy lệnh tại thư mục gốc Smart-Green. Giữ bản bringup với `ENABLE_PUMP_TEST = false` trong giai đoạn thu này.

## 1. Thu một phiên mới

Cố định cảm biến, kiểm tra đồng hồ laptop và đóng PlatformIO Serial Monitor. Chỉ một chương trình mở cổng Serial tại một thời điểm.

```bash
source .venv-ai/bin/activate
python -m pip install -e '.[capture]'
python tools/capture_serial.py /dev/ttyUSB0 --seconds 60 --output firmware/data/session01.jsonl
```

Nếu chưa có môi trường Python, tạo bằng `python3 -m venv .venv` rồi kích hoạt `.venv/bin/activate` thay cho `.venv-ai`.

Logger xác thực mẫu trước khi ghi; thêm `received_at` UTC và giữ nguyên `timestamp` từ ESP32. Bản bench có `timestamp=null`. Nhiều mẫu nhận trong cùng một lần đọc Serial có thể có cùng `received_at`; đây không phải thời gian đo chính xác. Mở Serial có thể làm thiết bị reset; `boot_id` phân biệt các phiên khởi động.

Bỏ `--seconds 60` để ghi liên tục và dừng bằng Ctrl+C. File được ghi nối tiếp; dùng tên phiên mới để dễ quản lý. Logger báo số mẫu lưu và dòng bị bỏ. Không có thiết bị thì chỉ chạy bước xử lý log bên dưới.

## 2. Làm sạch và xem báo cáo

```bash
python3 firmware/tool/parse_logs.py firmware/data/session01.jsonl --output firmware/data/prepared/session01.csv
```

Không truyền file đầu vào thì parser chọn log mới nhất trong `firmware/logs`, bất kể thư mục đang đứng. Có thể truyền nhiều file theo thứ tự thu để kiểm tra trùng xuyên file:

```bash
python3 firmware/tool/parse_logs.py firmware/logs/*.log --output firmware/data/prepared/bench_clean.csv
```

Ba đầu ra:

- `.csv`: bản ghi qua kiểm tra, giữ giá trị null thành ô trống.
- `.quality.json`: số mẫu, dòng bị từ chối kèm file/dòng/lý do, bản trùng, khoảng sequence bất thường, thời gian lùi và số giá trị thiếu.
- `.postgres.csv`: các cột định danh, measured_at, received_at và payload JSON phục vụ TV2 nhập staging. Chưa tự kết nối hoặc ghi database.

Parser loại JSON lỗi, khóa JSON lặp, sai kiểu, ADC ngoài 0–4095, phần trăm ngoài 0–100 và cờ hợp lệ mâu thuẫn. Trường cảm biến nullable vẫn phải có mặt; thiếu giờ đo/giờ nhận được báo trong `missing`, không suy đoán từ tên file hay thời gian xử lý.

Cùng `device_id + boot_id + sample_seq` và cùng payload (bỏ qua `received_at`) là bản trùng. Nếu payload khác, giữ bản đầu, từ chối bản sau và báo `conflicting duplicate identity`; cần xem log gốc trước khi dùng dữ liệu này. Khoảng sequence là bất thường theo thứ tự đầu vào, không mặc định đều là mất mẫu. Các lần boot và thiết bị được kiểm tra riêng.

Đầu ra cùng tên sẽ được ghi đè khi xử lý lại. Dùng thư mục phiên riêng để giữ các lần phân tích. Log nguồn được giữ nguyên. Báo cáo luôn để `ai_ready=false`: qua xác thực định dạng không đủ để xác nhận đủ dữ liệu huấn luyện.

## 3. Điều kiện bắt đầu thu dài hơn

- Có mẫu `soil_valid=true`, `soil_pct` khác null và mốc hiệu chuẩn đúng với vị trí lắp.
- `received_at` có múi giờ; xem xét các dòng bị từ chối và khoảng mất mẫu.
- Giữ nhật ký tưới tay: thời gian có múi giờ, device/calibration ID, lượng nước ml nếu đo được và ghi chú. Không biết lượng nước thì để null.
- Ghi lại mọi lần di chuyển cảm biến, thay đất, đổi chậu hoặc reset thiết bị.
- Thu qua nhiều chu kỳ khô–tưới. AI hiện chưa dùng trực tiếp lượng nước tưới tay; không quy đổi thành thời gian bơm giả.

## 4. Bàn giao TV2

Bàn giao CSV staging, báo cáo chất lượng, cấu trúc telemetry trong `docs/TV2_CONTRACT.md` và thông tin hiệu chuẩn. TV2 cần duy trì khóa duy nhất `(device_id, boot_id, sample_seq)`, phân biệt giờ đo/giờ nhận/giờ nhập database và giữ null của thời gian không biết. Script `db/import_bench.sql` hiện chứa đường dẫn mẫu cũ; cần chọn đúng file nguồn trước khi chạy với database phát triển.

## 5. Kiểm thử không cần ESP32

```bash
python -m pytest -q tools/tests/test_prepare_telemetry.py tools/tests/test_capture_serial.py
```

Kiểm thử dùng dữ liệu giả lập và cổng nhập giả lập ở mức hàm; không xác nhận thiết bị thật hoặc PostgreSQL đã hoạt động.

## Kết quả rà soát log đang có — 07/11/2026

Chạy parser trên 42 file `firmware/logs/*.log` trong máy phát triển:

| Chỉ số | Kết quả |
| --- | ---: |
| Bản ghi qua kiểm tra cấu trúc | 586 |
| Phiên device/boot | 15 |
| Bản ghi `soil_valid=true` | 133 |
| Bản ghi `soil_valid=false` | 453 |
| Dòng không hợp lệ / không phải JSON | 231167 |
| Bản trùng loại bỏ | 0 |
| Bất thường sequence theo thứ tự đầu vào | 12 |
| Mẫu thiếu cả giờ đo và giờ nhận | 586 |

Số dòng bị loại gồm thông báo Serial và dữ liệu không phân tích được, không đồng nghĩa có 231167 mẫu cảm biến bị mất. 586 mẫu hợp lệ về cấu trúc cũng không đồng nghĩa đều hợp lệ để huấn luyện. Không gán giờ từ tên file cho các mẫu này.

Kết quả cục bộ: `firmware/data/review-2026-11-07/bench_clean.csv`, cùng báo cáo `.quality.json` và CSV staging `.postgres.csv`. Các file dữ liệu này được Git bỏ qua. Chưa nhập PostgreSQL và chưa thu một phiên mới từ thiết bị trong lần triển khai này.
