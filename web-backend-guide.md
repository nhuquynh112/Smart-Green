# HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG HỆ THỐNG BACKEND, DATABASE & WEB DASHBOARD (TV2)

Tài liệu này hướng dẫn chi tiết cách cài đặt môi trường, khởi tạo cơ sở dữ liệu PostgreSQL, chạy FastAPI server, nạp dữ liệu mô phỏng và giải thích ý nghĩa toàn bộ các thành phần trên giao diện Web Dashboard của dự án **Smart-Green (Smart Garden)**.

---

## I. YÊU CẦU MÔI TRƯỜNG

- **Python:** 3.11+ (Khuyến nghị 3.13 theo môi trường bundle AI v2).
- **Database:** PostgreSQL 15+ (có thể chạy qua Docker Desktop hoặc cài trực tiếp). Hệ thống hỗ trợ tự động chuyển về SQLite cục bộ/in-memory khi chạy kiểm thử (`pytest`).
- **Trình duyệt:** Chrome, Edge hoặc Firefox.

---

## II. HƯỚNG DẪN CÀI ĐẶT TỪ ĐẦU (STEP-BY-STEP)

### Bước 1: Kích hoạt môi trường ảo và cài đặt thư viện
Mở **Git Bash** (Windows) hoặc Terminal (Linux/macOS) tại thư mục gốc của repository `Smart-Green`:

```bash
# Tạo và kích hoạt môi trường ảo
python -m venv .venv
source .venv/Scripts/activate   # Trên Linux/macOS: source .venv/bin/activate

# Bật chế độ UTF-8 (bắt buộc trên Windows để xử lý tiếng Việt trong subprocess)
export PYTHONUTF8=1

# Cài đặt gói dự án cùng các thư viện Backend
python -m pip install -e ".[test,report]"
pip install fastapi uvicorn psycopg2-binary python-dotenv apscheduler requests
```

### Bước 2: Khởi chạy PostgreSQL (Qua Docker)
Nếu máy đã cài **Docker Desktop**, chạy lệnh sau để dựng nhanh PostgreSQL:

```bash
docker start smart-garden-pg || docker run --name smart-garden-pg \
  -e POSTGRES_PASSWORD=gardenpass \
  -e POSTGRES_DB=smart_garden \
  -p 5432:5432 -d postgres:15
```

Cấu hình biến môi trường kết nối Database và thông tin quản trị:

```bash
export DATABASE_URL="postgresql://postgres:gardenpass@localhost:5432/smart_garden"
export SG_WEB_USER="admin"
export SG_WEB_PASSWORD="smartgreen2026"
export SG_MAX_PULSE_MS="1000"
```

### Bước 3: Khởi tạo Schema, Nạp dữ liệu mẫu & Tạo Model AI v2
```bash
# 1. Tạo artifacts mô hình AI v2 (nếu chưa có thư mục artifacts/offline-demo-v2)
python tools/demo_offline.py --days 10 --output artifacts/offline-demo-v2

# 2. Kiểm tra kết nối PostgreSQL và tự động tạo 5 bảng production (db/schema.sql)
python -m backend.check_db

# 3. Nạp dữ liệu mẫu (gồm kịch bản Cây Cẩm nhung Fittonia và 14.400 mẫu SIM-ONLY)
python -m backend.seed_demo
```

### Bước 4: Khởi động FastAPI Server & Thiết bị giả lập
Mở **Terminal 1** để chạy Web Server:
```bash
export PYTHONUTF8=1
export DATABASE_URL="postgresql://postgres:gardenpass@localhost:5432/smart_garden"
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

*(Tuỳ chọn)* Mở **Terminal 2** để chạy script giả lập mạch ESP32 gửi dữ liệu thời gian thực và tự động nhận/ACK lệnh điều khiển từ Web:
```bash
source .venv/Scripts/activate
export PYTHONUTF8=1
python -m backend.simulate_device
```

Truy cập giao diện Web Dashboard tại: **`http://localhost:8000`**

---

## III. HƯỚNG DẪN SỬ DỤNG GIAO DIỆN WEB & GIẢI THÍCH Ý NGHĨA

Giao diện Web Dashboard được chia thành **6 khu vực chức năng chính**, thiết kế bám sát hợp đồng giao tiếp phần cứng ESP32 và nguyên tắc an toàn của hệ thống:

### 1. Thanh điều hướng & Chọn thiết bị (Topbar & Device Selector)
- **Đăng nhập quản trị (`admin` / `smartgreen2026`):**
  - Khi chưa đăng nhập, người xem vẫn theo dõi được toàn bộ số liệu cảm biến, biểu đồ và kết quả AI.
  - Khi cần gửi lệnh điều khiển xuống ESP32 (`Tưới ngay`, `Cập nhật chế độ`, `Dừng bơm · STOP`) hoặc bấm `Chạy dự đoán AI`, hệ thống yêu cầu xác thực quản trị viên qua hộp thoại nội bộ trên trang.
- **Menu chọn thiết bị (Góc phải phía trên):**
  - **`Cây Cẩm nhung (Fittonia) · Kịch bản Bench`:** Hiển thị dữ liệu theo cấu hình phần cứng thực tế (`calibration_id: fittonia-dry2511-wet979-v1`). Dùng khi theo dõi và điều khiển mạch ESP32 thật.
  - **`Mô phỏng AI v2 (SIM-ONLY · 14.400 mẫu)`:** Bộ dữ liệu chuỗi thời gian 10 ngày khớp metadata với bundle `candidate.joblib`, dùng để kiểm chứng và trình diễn luồng dự đoán Machine Learning 30 phút.

---

### 2. Cụm 5 Thẻ Cảm Biến Thời Gian Thực
Hiển thị trạng thái môi trường mới nhất từ bản ghi `telemetry` của ESP32:

| Thẻ hiển thị | Ý nghĩa các chỉ số trên thẻ |
| :--- | :--- |
| **1. Độ ẩm đất (`%`)** | - **Số phần trăm lớn (VD: `43,01 %`):** Độ ẩm đất tương đối quy đổi theo công thức nội suy tuyến tính giữa 2 mốc hiệu chuẩn.<br>- **`ADC 1.852 · Mốc khô/ướt: 2.511 / 979`:** Giá trị điện áp thô đọc từ chân `GPIO34`. Giá trị ADC càng lớn đất càng khô (`2511` là đất khô kiệt `0%`, `979` là đất bão hòa nước `100%`).<br>- **Nhãn `Cảm biến hợp lệ` (`soil_valid`):** Báo hiệu cảm biến hoạt động bình thường. Nếu đứt dây hoặc chập mạch (`soil_valid = false`), hệ thống sẽ tự động khóa bơm. |
| **2. Nhiệt độ (`°C`)** | Nhiệt độ môi trường không khí xung quanh chậu cây đọc từ cảm biến `DHT22` (`GPIO27`), là đặc trưng đầu vào quan trọng để AI ước lượng tốc độ bay hơi nước. |
| **3. Độ ẩm không khí (`%`)** | Độ ẩm tương đối của không khí từ cảm biến `DHT22`. Độ ẩm không khí thấp kết hợp nhiệt độ cao sẽ làm đất khô nhanh hơn. |
| **4. Ánh sáng (`ADC thô`)** | Giá trị ADC đọc từ cảm biến quang trở (`GPIO35`, thang `0 – 4095`). Hiển thị rõ chú thích `ADC thô · Chưa quy đổi lux` để đảm bảo tính trung thực của số đo phần cứng. |
| **5. Phao mực nước (`GPIO26`)** | - **`Đủ nước · Phao an toàn`:** Bình chứa còn nước, cho phép máy bơm hoạt động.<br>- **`Hết nước`:** Khi công tắc phao báo cạn nước, cả Backend lẫn ESP32 sẽ **khóa cứng lệnh bơm** nhằm chống cháy máy bơm mini. |

---

### 3. Biểu đồ Diễn biến Cảm biến & Khung Điều khiển Thiết bị
- **Biểu đồ `Diễn biến cảm biến`:**
  - Trực quan hóa chuỗi thời gian của **Độ ẩm đất (%)** (trục tung trái, đường màu xanh lá) và **Nhiệt độ (°C)** (trục tung phải, đường màu cam).
  - Giúp quan sát rõ độ dốc khi đất khô tự nhiên và bước nhảy vọt của độ ẩm ngay sau mỗi xung tưới.
- **Khung `Điều khiển thiết bị`:**
  - **Trạng thái `Online` / `Offline`:** Thiết bị được tính là `Online` khi gửi telemetry đều đặn mỗi 60 giây. Nếu mất liên lạc quá ngưỡng quy định, Web báo `Offline` và mạch ESP32 tự động duy trì chế độ dự phòng tại chỗ.
  - **Chọn chế độ (`OFF` / `MANUAL` / `AUTO`) + nút `Cập nhật`:**
    - `OFF`: Vô hiệu hóa bơm tự động.
    - `MANUAL`: Chỉ bơm khi có lệnh thủ công từ Web.
    - `AUTO`: ESP32 tự động bơm theo ngưỡng Hysteresis (bật xung bơm khi độ ẩm `< 35%`, ngắt và chờ nước ngấm khi đạt ngưỡng an toàn) ngay cả khi mất kết nối Internet.
  - **Tưới thủ công (giây) + nút `Tưới ngay`:** Gửi lệnh `WATER` xuống hàng đợi. Backend tự động kiểm tra phao nước, cờ `soil_valid` và cắt giới hạn thời gian bơm theo ngưỡng an toàn (`SG_MAX_PULSE_MS`, mặc định `1000 ms` = `1 giây`).
  - **Nút `Dừng bơm · STOP`:** Phát lệnh ngắt bơm khẩn cấp ưu tiên cao xuống ESP32.

---

### 4. Khu vực AI Hỗ trợ Quyết định Tưới & Bảng So sánh Mô hình
- **Ô kiểm `Tôi đã đối soát đầy đủ lịch sử tưới của thiết bị này` (`watering_history_complete`):**
  - Chốt chặn an toàn dữ liệu của Pipeline AI v2: Vì sự kiện tưới làm thay đổi đột ngột độ ẩm đất, AI chỉ được phép chạy dự đoán khi người vận hành xác nhận lịch sử tưới trong 15 phút gần nhất đã được ghi nhận đầy đủ và không có xung tưới nào đang diễn ra.
- **Kết quả Dự đoán (VD: `33,72%` sau 30 phút):**
  - Cho biết độ ẩm đất dự kiến sau **30 phút nữa** với điều kiện **không tưới thêm** (`conditional_on: no_additional_irrigation`).
  - **Nhãn `Nguồn: Dữ liệu giả lập (synthetic) · Khóa tự động bật bơm (can_trigger_pump=false)`:** Đảm bảo nguyên tắc an toàn — mô hình huấn luyện trên dữ liệu giả lập chỉ đưa ra khuyến nghị hiển thị trên Web, tuyệt đối không tự ý kích hoạt máy bơm trên cây thật.
- **Bảng `So sánh mô hình` (Đánh giá bằng chỉ số MAE - Mean Absolute Error):**
  - So sánh sai số tuyệt đối trung bình (điểm %, **càng nhỏ càng chính xác**) trên tập kiểm thử chia theo thời gian:
    1. `Baseline 1: Giữ nguyên (Persistence)`: Giả định độ ẩm sau 30 phút bằng đúng độ ẩm hiện tại (`MAE = 0,74%`).
    2. `Baseline 2: Ngoại suy tuyến tính (Linear Extrapolation)`: Kẻ đường thẳng theo tốc độ khô hiện tại (`MAE = 0,06%`).
    3. `Linear Regression · Được chọn`: Mô hình Hồi quy tuyến tính học từ đa đặc trưng (`MAE = 0,04%` — thấp nhất nên được bundle chọn làm model chính).
    4. `Random Forest`: Mô hình Rừng ngẫu nhiên (`MAE = 0,16%`).

---

### 5. Lịch sử Tưới (`watering_events`) & Hàng đợi Lệnh (`commands`)
- **Bảng `Lịch sử tưới`:**
  - Chỉ ghi nhận các lần bơm **đã thực sự diễn ra dưới phần cứng** do ESP32 báo cáo lên qua API `POST /events`.
  - Hiển thị rõ Thời điểm, Nguồn kích hoạt (`Thủ công` / `Tự động`), Lý do và Thời lượng bơm thực tế (`actual_ms`). Nếu ESP32 bị mất điện/khởi động lại giữa chừng khi đang bơm (`reason = Reboot`), cột Thực tế sẽ ghi nhận trạng thái gián đoạn.
- **Bảng `Hàng đợi lệnh`:**
  - Theo dõi vòng đời của mọi lệnh điều khiển từ lúc tạo ra trên Web cho đến khi ESP32 xác nhận:
    - `PENDING`: Lệnh mới tạo, đang chờ ESP32 lấy về qua `GET /commands/next`.
    - `ACKED`: ESP32 đã nhận lệnh, kiểm tra điều kiện an toàn và gửi phản hồi xác nhận (`POST /commands/{seq}/ack`).
    - `EXPIRED`: Lệnh đã quá thời hạn hiệu lực **60 giây (TTL)** mà ESP32 chưa nhận (ví dụ khi mạch đang tắt nguồn hoặc mất Wi-Fi). Các lệnh `EXPIRED` sẽ bị hủy bỏ hoàn toàn để **chống tưới bù/tưới trùng** khi mạch có mạng trở lại.

---

### 6. Khung Trạng thái Thiết bị & Đồng bộ (Cuối trang)
Dùng để kiểm tra sức khỏe hệ thống nhúng (System Health) và tính toàn vẹn dữ liệu:
- **`Phiên khởi động (boot_id)` & `Số thứ tự mẫu (sample_seq)`:** Bộ định danh duy nhất `(device_id, boot_id, sample_seq)` giúp Backend chống lưu trùng bản ghi khi mạng chập chờn.
- **`Lệnh gần nhất (last_command_seq)`:** Số thứ tự lệnh cuối cùng mà ESP32 đã xử lý, giúp chống thực thi lặp lại cùng một lệnh.
- **`Sự kiện chờ gửi (queued_events)`:** Số sự kiện tưới đang lưu tạm trong bộ nhớ ESP32 chờ đẩy lên Server khi có mạng.
- **`Lỗi lưu trữ (storage_fault)` & `Đồng hồ hệ thống (clock_ready)`:** Giám sát lỗi bộ nhớ Flash (NVS/LittleFS) và trạng thái đồng bộ thời gian thực trên vi điều khiển.

---

## IV. CÁC LỆNH KIỂM THỬ & VẬN HÀNH NHANH

```bash
# Chạy toàn bộ bộ kiểm thử tự động (Unit test + API contract test)
PYTHONUTF8=1 python -m pytest -q --ignore=integration/test_http_runtime.py

# Sao lưu toàn bộ Database (Yêu cầu kỹ thuật số 8)
python -m backend.backup_db
```