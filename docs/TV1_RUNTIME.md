# Firmware vận hành TV1 — bản chờ nghiệm thu

Cập nhật 06/11/2026. Đã viết và kiểm thử offline, chưa upload và chưa nghiệm thu trên mạch. Bản `bringup` và các mốc hiệu chuẩn trong namespace NVS `sg-bench` được giữ riêng.

## Phần đã triển khai

| Phần | Cách hoạt động |
|---|---|
| Cảm biến | GPIO34 đất, GPIO35 LDR, GPIO27 DHT22, GPIO26 phao; task riêng đọc đất/ánh sáng khoảng mỗi giây, DHT khoảng 3 giây |
| Hiệu chuẩn | Hai mốc trong cấu hình site; chưa có mốc hoặc chưa xác nhận thì soil_valid=false, soil_pct=null |
| Điều khiển | Lõi OFF/MANUAL/AUTO; ba mẫu khô liên tiếp, ngưỡng dừng, cooldown, giới hạn xung và cửa sổ quota 24h |
| GPIO | Tắt relay trước ghi NVS khi dừng. Đo thời gian GPIO thực sự được bật để ghi actual_ms; không phải đo lưu lượng thật |
| Guard | Task esp_timer kiểm tra mỗi 10ms: hết thời gian xung, phao cạn, heartbeat main trễ hơn 500ms. Heartbeat lỗi khóa tưới đến reboot |
| Mạng | Task riêng; Wi-Fi thử kết nối lại; HTTP có thời gian chờ và giới hạn response 4096 byte; không gọi HTTP trong vòng quyết định bơm |
| Giờ | NTP UTC; trước đồng bộ timestamp=null và khóa lệnh bật. Sau đồng bộ, mất Wi-Fi vẫn giữ đồng hồ hệ thống; bước nhảy >10 giây được phát hiện trong loop sẽ khóa tưới đến reboot |
| Telemetry | Khoảng 60 giây/lần; timestamp của lần đọc cảm biến, boot_id/sample_seq, calibration_id, cờ lỗi và trạng thái |
| Lệnh | WATER, SET_MODE, STOP; kiểm tra kiểu, device_id, sequence, TTL, duration và source/mode; sequence thực thi lưu NVS |
| ACK/sự kiện | Thử gửi lại khi lỗi; sự kiện giữ NVS đến ACK đúng event_id; lệnh đã thực thi có thể nhận lại sau reset nhưng không tưới lại |
| AI | Lệnh AI khóa riêng mặc định. Chỉ xem xét bật sau đánh giá thật và nghiệm thu tích hợp |

Guard là phần mềm chạy task riêng, **không phải mạch cắt nguồn độc lập**. Nó không bảo vệ được relay dính tiếp điểm, CPU treo hoàn toàn hoặc mức GPIO không xác định lúc boot. Khoảng 10ms là chu kỳ đặt timer, chưa phải sai số đã đo trên phần cứng.

## 1. Build, không cần thiết bị

```bash
cd /home/ad/Desktop/Smart-Green
/home/ad/.platformio/penv/bin/pio run -d firmware -e esp32dev
bash tools/test_firmware.sh
.venv-ai/bin/python -m pytest -q ai/tests tools/tests
```

- `esp32dev`: runtime mới, `src/main.cpp`.
- `bringup`: chương trình thử mạch cũ, `src/bringup.cpp` → `bringup/bringup.ino`.
- Không thêm `-t upload` khi chỉ kiểm thử trên máy.

Các test native kiểm tra logic, không giả làm kiểm chứng FreeRTOS, Wi-Fi/HTTP hay GPIO thật. Test Python kiểm tra hợp đồng API mô phỏng và pipeline AI/data.

## 2. Cấu hình local khi chuẩn bị tích hợp

Chép `firmware/include/site_config.example.h` thành `firmware/include/site_config.h` rồi điền trên máy. File local được gitignore; không gửi Wi-Fi password/API key vào chat hay commit.

- `SG_WIFI_SSID`, `SG_WIFI_PASSWORD`: Wi-Fi 2.4GHz.
- `SG_BACKEND_URL`: địa chỉ laptop/server mà ESP32 truy cập được; không dùng localhost; không có dấu `/` cuối.
- `SG_DEVICE_ID`, `SG_API_KEY`: khớp thiết bị mà TV2 cấp quyền.
- HTTPS cần `SG_ROOT_CA` PEM; không dùng setInsecure. HTTP chỉ được mở chủ động bằng `SG_ALLOW_LAN_HTTP=true` trên mạng phát triển tin cậy; truyền API key không mã hóa.
- `SG_DRY_RAW`, `SG_WET_RAW`, `SG_CALIBRATION_ID`: mốc đất thật và phiên hiệu chuẩn. Không tự lấy giá trị ngoài không khí, không tự nhập từ bench NVS.
- `SG_CALIBRATION_VERIFIED`: chỉ true sau hiệu chuẩn; cho phép đọc soil_pct.
- `SG_HARDWARE_VERIFIED`: chỉ true sau xác nhận relay, phao, boot/reset OFF, lưu lượng và các hạn mức. Cả hai cờ phải true, mốc hợp lệ và cấu hình core hợp lệ mới có thể bật output.
- `SG_AI_COMMANDS_ENABLED`: giữ false cho tới khi đủ nghiệm thu AI.

Các ngưỡng/thời gian trong template chỉ để build được. Chọn lại từ đất/cây và bơm thật. `aiCeiling` hiện bằng ngưỡng khô `low`, nên AI chưa được phép tưới sớm ở độ ẩm cao hơn ngưỡng; nếu muốn dùng tưới sớm phải thống nhất, cấu hình và kiểm thử riêng.

Lần boot đầu mode OFF. Đổi chế độ qua SET_MODE sau khi đồng bộ giờ. Namespace vận hành là `smartgreen-v1`, tách khỏi hiệu chuẩn bench; không tự xóa NVS để vượt hạn mức. Đổi device_id khi xóa nhật ký/sequence NVS để tránh trùng event ID tại server.

## 3. Hành vi khi lỗi

- Mất mạng: AUTO vẫn chạy Auto-Rule với cảm biến/clock hợp lệ; không chờ server trong vòng điều khiển. OFF vẫn OFF, MANUAL không tự thành AUTO. `server_available=false` khi không có phản hồi HTTP 2xx quá 60 giây.
- Mất điện rồi không có mạng/NTP: chưa biết UTC → khóa tưới. RTC ngoài chưa triển khai.
- Cạn nước/đứt dây phao: open → tank_ok=false, ngắt/chặn bơm. Đấu phao đóng khi đủ nước.
- ADC sát rail hoặc stale: không dùng để tưới. Đứt dây analog có thể cho giá trị giữa dải, nên phần mềm chưa phát hiện chắc chắn mọi lỗi dây.
- Reset giữa lần tưới: GPIO cần OFF nhờ cấu hình điện đã đo; sự kiện Reboot có actual_ms=null, quota dự trù giữ nguyên.
- Nhật ký đủ 32 sự kiện chưa ACK: chặn tưới mới. Quota là cửa sổ 24 giờ cố định bắt đầu ở lần tưới đầu, không phải mọi cửa sổ trượt 24 giờ.
- NVS lỗi: tắt/khóa output; không reset quota âm thầm. Định dạng State vẫn là prototype nhị phân, chưa có migration hoặc checksum ứng dụng.
- Telemetry: một gói đang retry + một slot mới nhất. Mạng mất lâu có thể mất mẫu; `telemetry_overwrites` và sequence giúp nhận diện. Không có bộ đệm telemetry lưu flash, không hứa dữ liệu đầy đủ qua mất điện/mất mạng.
- Guard dừng ghi thời gian GPIO bật. Đây không chứng minh bơm đã quay hay có nước chảy; không tính lượng nước từ số này trước khi đo lưu lượng.

## 4. Backend mô phỏng để TV2 đối chiếu

`tools/mock_tv2.py` chỉ là trình mô phỏng hợp đồng, không thay FastAPI/PostgreSQL. Mặc định bind localhost, mọi dữ liệu nằm RAM và mất khi thoát. Không dùng cho thu dataset thật.

```bash
cd /home/ad/Desktop/Smart-Green
read -rsp 'Mock API key: ' SMART_GREEN_MOCK_KEY
export SMART_GREEN_MOCK_KEY
python3 tools/mock_tv2.py --port 8000
```

Không có file commands thì GET next trả 204. Có thể truyền `--commands /duong/dan/commands.json` chứa danh sách lệnh theo TV2_CONTRACT.md. Không tái dùng mock sequence với thiết bị thực đã có NVS production. `--host 0.0.0.0` chỉ dùng khi chủ động thử trên LAN và đã kiểm tra truy cập.

## 5. Những gì còn phải nghiệm thu

Chưa nạp bản runtime này. Chưa thử end-to-end HTTP thật với ESP32/TV2, NTP khi mất mạng, độ trễ GPIO/guard, nguồn bơm, reset/quota trên flash, ACK sau reboot hay thời gian chạy dài. Cần hoàn thành các mục trên với relay chưa gắn bơm trước, rồi mới thử bơm có giám sát. Không bật cờ commissioning chỉ vì build/test đạt.

## Kết quả kiểm chứng lần cập nhật này

- Build PlatformIO `esp32dev`: SUCCESS; `bringup`: SUCCESS (06/11/2026).
- `bash tools/test_firmware.sh`: cả bộ controller và runtime đều đạt, compiler C++17 bật `-Wall -Wextra -Werror`.
- `.venv-ai/bin/python -m pytest -q ai/tests tools/tests`: **24 passed**.
- Build dùng cấu hình mặc định khóa output; chưa có site_config.h local, không sử dụng thông tin Wi-Fi/API thật.
- Không có thao tác upload, bật bơm hoặc mở cổng Serial trong lần triển khai runtime này.
