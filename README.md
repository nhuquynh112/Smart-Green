# Smart-Green — Smart Garden

**Hệ thống tưới cây thông minh tích hợp IoT và AI**, sử dụng ESP32 để theo dõi môi trường trồng cây, thu thập dữ liệu và phát triển cơ chế tưới có kiểm soát.

Dự án hướng đến một hệ thống gồm thiết bị IoT, FastAPI backend, PostgreSQL, dashboard web và mô hình dự đoán độ ẩm đất trước 30 phút. AI cung cấp đề xuất; ESP32 chịu trách nhiệm kiểm tra điều kiện và giới hạn an toàn trước khi điều khiển bơm.

> **Trạng thái ngày 07/11/2026:** Đã hoàn thành kiểm thử phần cứng cơ bản, hiệu chuẩn cảm biến độ ẩm đất và thử bơm nước thực tế. Chưa triển khai tưới tự động lên cây hoặc điều khiển bơm từ web. Firmware thử nghiệm đang khóa bơm với `ENABLE_PUMP_TEST = false`.

## Mục tiêu

- Theo dõi độ ẩm đất, nhiệt độ, độ ẩm không khí, ánh sáng và mực nước.
- Lưu dữ liệu theo thời gian để quan sát môi trường và đánh giá nhu cầu tưới.
- Cung cấp dashboard theo dõi cảm biến, lịch sử tưới và điều khiển thủ công có xác nhận.
- Xây dựng Auto-Rule với hysteresis, khoảng nghỉ và hạn mức tưới.
- Dự đoán độ ẩm đất sau 30 phút, so sánh với baseline và đánh giá bằng MAE.

## Tiến độ hiện tại

| Hạng mục | Trạng thái |
| --- | --- |
| Cảm biến, relay và máy bơm | Đã lắp ráp và kiểm thử cơ bản trên phần cứng |
| Firmware `bringup` | Đã thử đọc cảm biến, xuất JSON, hiệu chuẩn và bơm có giám sát |
| Firmware vận hành `esp32dev` | Đã có mã cho điều khiển, mạng và các cơ chế bảo vệ; còn cần nghiệm thu trên thiết bị và backend thật |
| Thu thập và xử lý dữ liệu | Có log Serial và công cụ xử lý; cần hoàn thiện kiểm tra chất lượng dữ liệu thực |
| PostgreSQL | Có script nhập dữ liệu bench; chưa xác nhận đã nhập vào database |
| FastAPI và dashboard | Chưa triển khai hệ thống tích hợp; hiện có backend mô phỏng phục vụ kiểm thử |
| AI dự đoán độ ẩm | Có pipeline và mô hình thử nghiệm; dữ liệu thực chưa đủ để đánh giá hiệu quả |
| Tưới tự động trên cây | Chưa triển khai |

Việc đã có mã nguồn hoặc kiểm thử trên máy tính không thay thế nghiệm thu phần cứng và thử nghiệm toàn hệ thống.

## Kiến trúc hệ thống

Luồng đã kiểm thử:

```text
Cảm biến → ESP32 / bringup → Serial JSON → Log trên máy tính
                  │
                  └── Relay → Máy bơm (thử có giám sát, hiện đã khóa)
```

Kiến trúc mục tiêu:

```text
Cảm biến → ESP32 ←──── Wi-Fi / HTTP ────→ FastAPI ←──→ Dashboard web
             │                             │
             │                             ├── PostgreSQL
             │                             └── AI dự đoán / đề xuất tưới
             ▼
     Kiểm tra điều kiện an toàn
             │
             ▼
        Relay → Máy bơm
```

Định dạng telemetry, lệnh điều khiển và phản hồi được mô tả trong [hợp đồng tích hợp](docs/TV2_CONTRACT.md).

## Phần cứng

| Thiết bị | Kết nối ESP32 | Chức năng / kết quả kiểm thử |
| --- | --- | --- |
| Cảm biến độ ẩm đất | GPIO34 | Đọc ADC và hiệu chuẩn hai mốc |
| Cảm biến ánh sáng | GPIO35 | Đọc `light_raw`, phản ứng khi che và bỏ che |
| DHT22 | GPIO27 | Đọc nhiệt độ và độ ẩm không khí |
| Phao mực nước | GPIO26 | Phát hiện đủ nước / thiếu nước |
| Relay | GPIO25 | Đã kiểm thử bật / tắt |
| Máy bơm mini 3–5V | Qua tiếp điểm COM–NO của relay | Đã bơm nước qua ống |

**Nguồn cấp:** ESP32 dùng USB; relay và máy bơm dùng adapter 5V–2A. Hai cút PCT-213 được sử dụng để phân phối nguồn dương và âm.

**Cây thử nghiệm:** Cẩm nhung (*Fittonia*), trồng trong chậu có lỗ thoát nước. Cảm biến đã được thử trong đất thật; chưa vận hành tưới tự động cho cây.

### Hiệu chuẩn độ ẩm đất

| Thông số | Giá trị ghi nhận |
| --- | --- |
| Mốc khô `dry_raw` | `2511` |
| Mốc ướt `wet_raw` | `979` |
| Trạng thái `soil_valid` | `true` |
| Độ ẩm sau khi tưới chậu thử nghiệm | Khoảng `84–85%` |

Độ ẩm được nội suy giữa hai mốc và giới hạn trong khoảng 0–100%:

```text
soil_pct = clamp(100 × (soil_raw − dry_raw) / (wet_raw − dry_raw), 0, 100)
```

Đây là **độ ẩm tương đối theo hiệu chuẩn**, chưa phải hàm lượng nước tuyệt đối trong đất. Các mốc trên thuộc lần thử hiện tại, cần kiểm tra lại khi thay cảm biến hoặc điều kiện lắp đặt. Ánh sáng hiện sử dụng giá trị ADC, chưa quy đổi sang lux.

## Công nghệ

| Thành phần | Công nghệ | Mức độ triển khai |
| --- | --- | --- |
| Thiết bị IoT | ESP32, Arduino Framework, PlatformIO, C++ | Có firmware thử mạch và firmware vận hành chờ nghiệm thu |
| Xử lý dữ liệu | Python | Có công cụ thu Serial, làm sạch và kiểm tra dữ liệu |
| Backend | FastAPI | Dự kiến tích hợp |
| Cơ sở dữ liệu | PostgreSQL | Có script nhập dữ liệu bench |
| Giao diện | Dashboard web | Dự kiến phát triển |
| AI | pandas, NumPy, scikit-learn | Có baseline, Linear Regression và Random Forest |
| Kiểm thử | pytest, kiểm thử C++ native | Có bộ kiểm thử logic và tích hợp mô phỏng |

## Cấu trúc thư mục

```text
Smart-Green/
├── firmware/
│   ├── bringup/          # Chương trình kiểm thử phần cứng có giám sát
│   ├── src/              # Điểm vào bringup và firmware vận hành
│   ├── include/          # Điều khiển, cảm biến, giao thức và cấu hình
│   ├── test/native/      # Kiểm thử logic C++ trên máy tính
│   ├── tool/             # Script parse_logs.py
│   └── platformio.ini    # Hai môi trường: bringup và esp32dev
├── ai/                   # Pipeline dự đoán và kiểm thử AI
├── db/                   # SQL nhập dữ liệu bench
├── tools/                # Thu Serial, chuẩn bị dữ liệu, mô phỏng và báo cáo
├── integration/          # Kiểm thử tích hợp HTTP mô phỏng
├── tests/                # Dữ liệu mẫu phục vụ kiểm thử
├── docs/                 # Hướng dẫn kỹ thuật và tài liệu bàn giao
├── pyproject.toml        # Cấu hình gói Python và dependencies
└── README.md
```

Các thư mục dữ liệu cục bộ như `firmware/logs/`, `data/` và `artifacts/` phục vụ thu thập, xử lý hoặc xuất kết quả; chúng không phải dữ liệu mẫu bắt buộc có trong Git.

## Bắt đầu sử dụng

Các lệnh dưới đây chạy từ thư mục gốc repository, trừ khi có ghi chú khác. Ví dụ sử dụng Bash trên Linux.

### 1. Chuẩn bị môi trường Python

Yêu cầu Python 3.11 trở lên; kiểm thử firmware native cần trình biên dịch hỗ trợ C++17.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

### 2. Build firmware

```bash
python -m pip install platformio==6.1.18

# Firmware thử phần cứng
pio run -d firmware -e bringup

# Firmware vận hành chờ nghiệm thu
pio run -d firmware -e esp32dev
```

Hai lệnh trên chỉ biên dịch. Môi trường `bringup` dùng `firmware/bringup/bringup.ino`; môi trường `esp32dev` dùng `firmware/src/main.cpp`.

Để đọc thiết bị đã nạp firmware qua Serial:

```bash
pio device monitor -d firmware -e bringup
```

Cấu hình hiện dùng tốc độ `115200` baud và cổng `/dev/ttyUSB0`; điều chỉnh cổng nếu thiết bị được nhận ở địa chỉ khác.

Các lệnh Serial của bản `bringup`:

| Lệnh | Chức năng |
| --- | --- |
| `help` | Hiển thị danh sách lệnh |
| `status` | Xuất một bản ghi trạng thái JSON |
| `dry` / `wet` | Ghi lại mốc hiệu chuẩn khô / ướt |
| `arm` / `pump` | Cho phép một xung bơm thử khi các điều kiện được đáp ứng; hiện bị khóa bằng `ENABLE_PUMP_TEST = false` |
| `stop` | Dừng bơm và hủy trạng thái cho phép bơm thử |

Đọc [hướng dẫn firmware vận hành](docs/TV1_RUNTIME.md) và [checklist phần cứng](docs/HARDWARE_CHECKLIST.md) trước khi cấu hình, nạp hoặc nghiệm thu runtime.

### 3. Xử lý log Serial

Parser dùng chung bộ kiểm tra với `tools/prepare_telemetry.py`. Chạy từ thư mục gốc để xử lý log mới nhất:

```bash
python3 firmware/tool/parse_logs.py
```

Hoặc truyền nhiều file theo thứ tự thu để loại trùng giữa các file:

```bash
python3 firmware/tool/parse_logs.py firmware/logs/*.log --output firmware/data/prepared/bench_clean.csv
```

Đầu ra gồm CSV sạch, báo cáo `.quality.json` và CSV `.postgres.csv` để bàn giao nhập database. Parser kiểm tra trường bắt buộc, kiểu dữ liệu, phạm vi ADC/phần trăm, cờ hợp lệ và thời gian có múi giờ. Bản ghi trùng được nhận diện bằng `device_id + boot_id + sample_seq`; nếu nội dung xung đột, giữ bản đầu và báo lỗi để rà soát. Dữ liệu thiếu thời gian không được tự gán giờ hiện tại.

Thu mẫu mới kèm thời gian nhận UTC (đóng Serial Monitor trước):

```bash
python -m pip install -e '.[capture]'
python tools/capture_serial.py /dev/ttyUSB0 --seconds 60 --output firmware/data/session01.jsonl
python3 firmware/tool/parse_logs.py firmware/data/session01.jsonl --output firmware/data/prepared/session01.csv
```

Bỏ `--seconds 60` để thu liên tục, dừng bằng `Ctrl+C`. Logger chỉ đọc Serial, không gửi lệnh tưới. Xem [quy trình thu và kiểm tra dữ liệu](docs/TV1_DATA_COLLECTION.md).

Telemetry có các trường định danh `device_id`, `boot_id`, `sample_seq`, thời gian hoạt động `uptime_ms`, dữ liệu cảm biến và trạng thái bơm. Bản bench chưa có thời gian UTC từ thiết bị (`timestamp = null`); cần quản lý thời gian nhận dữ liệu và các lần khởi động khi xây dựng chuỗi thời gian.

Xem thêm [hướng dẫn hiệu chuẩn và thu dữ liệu thực](docs/CALIBRATION_AND_REAL_DATA.md) và công cụ `tools/prepare_telemetry.py`.

### 4. Kiểm thử trên máy tính

```bash
python -m pytest -q ai/tests tools/tests integration
bash tools/test_firmware.sh
```

Các bài kiểm thử này hỗ trợ xác minh pipeline dữ liệu, logic điều khiển và giao tiếp mô phỏng. Kết quả không chứng minh hệ thống đã vận hành ổn định với bơm, mạng và server thật.

### 5. Chạy thử pipeline AI

```bash
smart-green-simulate --days 10 --output data/synthetic.csv
smart-green-train data/synthetic.csv --horizon 30 --output artifacts/synthetic
```

Kết quả của lệnh trên sử dụng **dữ liệu giả lập**, chỉ phục vụ kiểm thử pipeline. Không sử dụng chúng làm bằng chứng về độ chính xác trên cây thật. Chi tiết nằm trong [AI runbook](docs/TV1_AI_RUNBOOK.md).

## Nguyên tắc điều khiển

- Phao báo thiếu nước phải ngăn bơm khởi động và được kiểm tra trong quá trình chạy.
- Mỗi lần tưới phải có giới hạn thời gian, khoảng nghỉ và hạn mức phù hợp với lưu lượng thực tế.
- Dữ liệu cảm biến không hợp lệ không được dùng để quyết định tưới.
- Điều khiển từ web cần có xác nhận, kiểm tra hiệu lực lệnh và chống thực thi lặp.
- Hành vi khi mất mạng, reset hoặc mất điện phải được nghiệm thu trước khi vận hành tự động.
- Đề xuất AI phải đi qua các điều kiện an toàn tại ESP32.

Firmware runtime đã có mã cho nhiều cơ chế trên, nhưng còn cần nghiệm thu thực tế. Bộ hẹn giờ phần mềm không thay thế mạch bảo vệ điện hoặc xử lý được mọi hỏng hóc cơ khí của relay.

## Lộ trình phát triển

1. **Hoàn thiện dữ liệu:** rà soát parser, xử lý dữ liệu lỗi / thiếu / trùng, hoàn thiện lưu trữ PostgreSQL và thu dữ liệu khi đất khô tự nhiên.
2. **Backend và dashboard:** xây dựng FastAPI, API nhận / truy vấn telemetry, giao diện cảm biến, lịch sử tưới và điều khiển thủ công có giới hạn.
3. **Tưới tự động:** nghiệm thu Auto-Rule, hysteresis, thời gian nghỉ, hạn mức và các tình huống thiếu nước / mất mạng trước khi thử trên cây.
4. **Đánh giá AI:** dự đoán trước 30 phút; so sánh baseline giữ nguyên giá trị gần nhất, xu hướng tuyến tính và mô hình ML bằng MAE trên dữ liệu chia theo thời gian.
5. **Hoàn thiện mô hình:** đo lưu lượng bơm, cố định phao / ống / cảm biến, bảo vệ mạch khỏi nước, thử toàn hệ thống và chuẩn bị báo cáo / demo.

## Tài liệu liên quan

- [Bàn giao tích hợp](docs/handoff/README.md)
- [Hợp đồng giao tiếp thiết bị – backend](docs/TV2_CONTRACT.md)
- [Firmware vận hành và giới hạn hiện tại](docs/TV1_RUNTIME.md)
- [Kiểm tra phần cứng](docs/HARDWARE_CHECKLIST.md)
- [Hiệu chuẩn và thu thập dữ liệu thực](docs/CALIBRATION_AND_REAL_DATA.md)
- [Thiết kế dữ liệu và AI](docs/DATA_AND_AI.md)
- [Hướng dẫn chạy pipeline AI](docs/TV1_AI_RUNBOOK.md)
- [Kết quả AI giả lập ngày 07/11/2026](docs/AI_OFFLINE_RESULTS_2026-11-07.md)
- [Kế hoạch triển khai TV1](docs/TV1_PLAN.md)
- [Nguồn tham khảo](docs/REFERENCES.md)

Các tài liệu chi tiết có thể ghi nhận tiến độ ở thời điểm trước; mốc tổng quan của README này là **07/11/2026**.
