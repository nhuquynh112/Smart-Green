# Ngày 3 — Wi-Fi, thời gian và telemetry mỗi phút

Trạng thái: đã chuẩn bị profile thu dữ liệu; chưa có ESP32 kết nối và chưa có API TV2 để nghiệm thu.

## 1. Thông tin cần chuẩn bị

TV2 cung cấp base URL server trên LAN (ví dụ http://192.168.1.10:8000), device_id và API key riêng. Endpoint nhận dữ liệu là `POST /api/v1/devices/{device_id}/telemetry`. ACK HTTP 2xx chỉ sau khi lưu thành công; cùng identity không tạo bản ghi mới. Máy ESP32 không dùng localhost để trỏ tới máy backend.

Trên máy này đã có `firmware/include/site_config.h` được Git bỏ qua, tạo từ `site_config.day3.example.h`. Điền Wi-Fi/API key trực tiếp trên máy, không gửi vào chat hay commit. Nếu clone mới, sao chép file example thành `site_config.h`.

| Cấu hình | Giá trị cần điền/xác nhận |
| --- | --- |
| SG_WIFI_SSID / SG_WIFI_PASSWORD | Wi-Fi thiết bị sẽ kết nối |
| SG_BACKEND_URL | Base URL, không có dấu / cuối hoặc đường dẫn /telemetry |
| SG_API_KEY / SG_DEVICE_ID | Đúng thông tin TV2 cấp |
| SG_ALLOW_LAN_HTTP | Chỉ true khi chủ động dùng HTTP trên LAN phát triển tin cậy |
| SG_ROOT_CA | CA PEM khi dùng HTTPS; không tắt xác minh chứng chỉ |
| SG_DRY_RAW / SG_WET_RAW | Đã điền 2511 / 979 theo phiên hiệu chuẩn trước; kiểm tra lại khi cắm cảm biến |
| SG_CALIBRATION_VERIFIED | Giữ false tới khi xác nhận cảm biến/vị trí và hai mốc vẫn đúng, sau đó mới true |
| SG_HARDWARE_VERIFIED / SG_AI_COMMANDS_ENABLED | Giữ false trong ngày 3 |
| SG_RELAY_ACTIVE_LOW | Example ngày 3 dùng false theo bringup đã thử; phải xác minh mức OFF thực tế |

Trong ngày 3, ngắt nguồn tải bơm trước khi nạp/thử runtime. Khóa phần mềm không khắc phục được đấu dây sai hoặc mức kích relay sai.

## 2. Build và nạp khi đã có thiết bị

Tại thư mục gốc repo, nếu `pio` chưa có trong PATH thì dùng `/home/ad/.platformio/penv/bin/pio` thay cho `pio`.

```bash
pio run -d firmware -e day3
```

Sau khi đã điền cấu hình, cắm ESP32, đóng các Serial Monitor và xác nhận nguồn tải bơm đã ngắt:

```bash
pio run -d firmware -e day3 -t upload --upload-port /dev/ttyUSB0
pio device monitor -d firmware -e day3 --port /dev/ttyUSB0
```

Đổi cổng nếu hệ điều hành nhận thiết bị khác. Chỉ lệnh có `-t upload` mới nạp; bước build không thay firmware trên mạch.

Profile `day3` kế thừa runtime nhưng compile-time khóa `allowPump`, kể cả khi vô tình bật các cờ commissioning. Không poll lệnh remote hoặc gửi nhật ký sự kiện bơm. Telemetry vẫn gửi mỗi 60 giây và lần đầu khi có mẫu cảm biến. SG_AI_COMMANDS_ENABLED không thể mở bơm trong profile này. Khi dùng `esp32dev`, khóa riêng day3 không còn — đó là bước nghiệm thu khác.

## 3. Đọc trạng thái

| Trường JSON | Ý nghĩa / mong đợi |
| --- | --- |
| build_stage | day3_telemetry_only |
| telemetry_only / commissioned / pump_on | true / false / false |
| wifi_connected | true khi đã kết nối Wi-Fi |
| clock_ready / clock_fault | true / false sau NTP thành công |
| timestamp | UTC có Z; có thể null trước đồng bộ giờ |
| soil_valid / soil_pct | true / phần trăm tương đối sau xác minh hiệu chuẩn |
| telemetry_http_status | 0: chưa thử; số âm: lỗi transport/config; 2xx: backend chấp nhận; 401/403: auth; 404: route; 5xx: server |
| telemetry_sent / telemetry_failures | Đếm số gói ACK 2xx / số lần gửi thất bại trong boot hiện tại |
| telemetry_overwrites | Gói trong hàng đợi bị thay bằng mẫu mới; có thể mất mẫu khi mất mạng lâu |

Số liệu HTTP trong JSON là trạng thái trước lúc gói hiện tại được gửi. Xem mẫu tiếp theo để biết lần trước đã thành công; đối chiếu server/DB mới xác nhận lưu bền. Không coi Wi-Fi connected là backend đã lưu dữ liệu.

Firmware retry gói chưa ACK với cùng identity. Có một gói đang chờ retry và một slot mới nhất; không có lưu telemetry bền qua mất điện. Dữ liệu thiếu phải được ghi nhận bằng sequence và log, không tuyên bố thu đủ khi mất mạng.

## 4. Thu bằng chứng

Đóng monitor rồi mở logger (không mở hai chương trình cùng cổng):

```bash
source .venv-ai/bin/activate
python tools/capture_serial.py /dev/ttyUSB0 --seconds 600 --output firmware/data/day3-session01.jsonl
python firmware/tool/parse_logs.py firmware/data/day3-session01.jsonl --output firmware/data/prepared/day3-session01.csv
```

Lần đầu chỉ thu 10 phút để kiểm tra cấu hình. Logger có thể làm thiết bị reset khi mở cổng; lưu boot_id mới. Không cần đợi đủ dữ liệu AI để kiểm tra giao tiếp.

## 5. Tiêu chí hoàn tất ngày 3

- [ ] ESP32 thật kết nối Wi-Fi, đồng bộ giờ, timestamp UTC hợp lệ.
- [ ] Nhận nhiều mẫu liên tiếp cách khoảng 60 giây, boot_id/sample_seq rõ ràng, không có bơm chạy.
- [ ] TV2 đối chiếu số mẫu và identity trong PostgreSQL; request lặp không nhân bản.
- [ ] Thử mất mạng ngắn khi bơm đã ngắt nguồn tải; ghi thời gian mất/phục hồi, sequence và số overwrite.
- [ ] Kết nối lại tự phục hồi gửi dữ liệu; khoảng mất mẫu hiện trong báo cáo, không điền giả.
- [ ] Lưu log, cấu hình không chứa bí mật, commit firmware và bằng chứng database.

Nếu TV2 chưa có API, vẫn có thể kiểm tra Wi-Fi/NTP/Serial, nhưng mục gửi và lưu DB còn chưa đạt. `tools/mock_tv2.py` chỉ giúp thử HTTP, không thay PostgreSQL hoặc nghiệm thu ngày 3.
