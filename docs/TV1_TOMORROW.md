# TV1 — chuẩn bị lắp và nạp ngày 05/11/2026

Mục tiêu buổi đầu: đọc đủ cảm biến, lưu hai mốc đất, kiểm tra phao, thử bơm 1 giây có giám sát và lưu log. Bản `bringup` chưa tự tưới, chưa gọi API và chưa phải firmware vận hành. Bản lõi điều khiển/AI cũ được giữ nguyên.

## 1. Chuẩn bị tối nay

- Cáp USB **có dữ liệu**, ESP32 WROOM-32 DevKit 30 chân; nếu C3/S3 thì dừng và đổi pin map/board.
- Arduino IDE hoặc PlatformIO; không cần Docker/PostgreSQL cho thử mạch.
- Bình đong, khay hứng, dây, nguồn bơm 5V đủ dòng, đồng hồ đo nếu mượn được.
- Bổ sung điện trở 10kΩ để kéo mức relay OFF (theo module); 4.7–10kΩ kéo DATA DHT22 lên 3.3V nếu dùng cảm biến rời.
- Mai gửi ảnh rõ hai mặt ESP32, relay, nhãn bơm/nguồn. Tên chân in trên module quyết định thứ tự nối, không suy theo màu dây/hình mẫu.

## 2. Pin map dự kiến — chỉ ESP32 WROOM-32 cổ điển

| Linh kiện | Chân linh kiện | ESP32/nguồn |
|---|---|---|
| Cảm biến đất điện dung | VCC / GND / AO | 3V3 / GND / GPIO34 |
| LDR module có AO, hỗ trợ 3.3V | VCC / GND / AO | 3V3 / GND / GPIO35 |
| DHT22 | VCC / GND / DATA | 3V3 / GND / GPIO27 |
| Phao tiếp điểm khô | Hai dây | GPIO26 và GND |
| Relay tương thích logic 3.3V | IN | GPIO25 |
| Relay | VCC / GND | Nguồn 5V ngoài / GND chung với ESP32 |

GPIO34/35 là đầu vào ADC1, phù hợp để sau này dùng Wi-Fi. Cấp cảm biến ở 3.3V chỉ khi model hỗ trợ; AO/DATA vào ESP32 không được ở mức 5V. LDR chỉ có DO không đo được chỉ số analog với bản này. Không nối nhầm chân 3V3 với 5V/VIN.

Phao phải **đóng mạch khi đủ nước**, mở khi cạn. Xoay/lật phao theo hướng dẫn sản phẩm nếu cần. Rút dây phải hiện `tank_ok=false`; không đổi logic thành mặc định đủ nước để vượt kiểm tra.

Relay: mặc định kích LOW. Chưa xác nhận module thì **chưa nối nguồn bơm**. Relay 5V không mặc nhiên nhận logic 3.3V; module kéo IN lên 5V hoặc có JD-VCC cần xem sơ đồ riêng. Kéo IN về mức OFF phù hợp với module, không kéo GPIO lên 5V.

Đường tải khi đã kiểm tra: `+5V nguồn → COM relay → NO relay → (+) bơm`; `(-) bơm → (-) nguồn`. Không dùng NC. Không lấy nguồn bơm từ ESP32/breadboard. Diode song song bơm: đầu có vạch về (+), đầu không vạch về (-); kiểm tra diode phù hợp dòng bơm. Tụ 470–1000µF song song nguồn gần tải, đúng cực, điện áp định mức lớn hơn 5V. ESP32 dùng USB; không nối thêm +5V ngoài vào board khi USB đang cấp.

## 3. Nạp bằng Arduino IDE

1. Cài board package **esp32 by Espressif Systems**; bản nguồn này được nhắm Arduino-ESP32 2.0.17 (PlatformIO pin tương ứng). Chọn ESP32 Dev Module và cổng USB đúng.
2. Library Manager: **ArduinoJson 7.3.1**, **DHT sensor library by Adafruit 1.4.6**, **Adafruit Unified Sensor 1.1.15**.
3. Mở `firmware/bringup/bringup.ino`.
4. Giữ `ENABLE_PUMP_TEST=false`. Nạp với bơm chưa nối nguồn. Upload speed 115200 nếu kết nối không ổn. Nếu treo Connecting, giữ BOOT lúc bắt đầu kết nối rồi thả khi ghi flash.
5. Serial Monitor 115200, line ending Newline. Mỗi 3 giây có JSON. Gõ `help`, `status`.

PlatformIO (từ thư mục gốc, khuyến nghị):

```bash
python3 -m venv .venv-tools
source .venv-tools/bin/activate
pip install platformio==6.1.18 pyserial==3.5
pio run -d firmware -e bringup
pio device list
pio run -d firmware -e bringup -t upload --upload-port /dev/ttyUSB0
pio device monitor -b 115200 -p /dev/ttyUSB0
```

Đổi cổng theo máy, thường `/dev/ttyUSB0` hoặc `/dev/ttyACM0`. Đóng monitor trước khi upload/logger. Nếu thiếu quyền cổng trên Ubuntu, thêm tài khoản vào nhóm `dialout` qua quản trị máy rồi đăng xuất/đăng nhập; không chmod 777.

## 4. Trình tự thực hành

1. **USB + ESP32:** nạp, xem JSON, reset; chưa cấp nguồn tải.
2. **Đất + DHT + LDR:** kiểm tra raw đất đổi khi thay độ ẩm; che/chiếu sáng thấy `light_raw` thay đổi; nhiệt/ẩm không khí hợp lý. LDR không phải lux. DHT lỗi trả null. ADC sát 0/4095 bị đánh dấu lỗi, nhưng cảm biến rút dây có thể vẫn ra số trôi: cờ này không chứng minh cảm biến còn cắm.
3. **Hiệu chuẩn:** đặt cảm biến cùng độ sâu ở đất khô tham chiếu, đợi raw ổn định, gõ `dry`; đặt vào đất đã tưới và thoát nước ổn định, gõ `wet`. Không nhúng phần điện tử vào nước. Hai mốc lưu NVS, qua reset vẫn còn. Cần chênh >=200 ADC; `soil_pct` là chỉ số tương đối, chưa phải độ ẩm thể tích. Ghi lại loại đất, độ sâu, raw và thời gian trong bảng bên dưới.
4. **Phao:** nâng/hạ và rút dây; đủ nước true, cạn/rút dây false.
5. **Relay không nối bơm:** xác minh kích LOW/HIGH, sửa `RELAY_ACTIVE_LOW` nếu cần. Kiểm tra reset và cấp nguồn chỉ relay vẫn OFF (đo COM–NO). Chỉ khi đúng mới đổi `ENABLE_PUMP_TEST=true` và nạp lại.
6. **Thử bơm:** đặt bơm chìm đúng mức, ống vào bình đong. Chờ >=10 giây từ boot/lần dừng. Gõ `arm`, trong 10 giây gõ `pump`: một xung 1000ms; gõ `stop` để ngắt sớm. Mỗi xung phải arm lại. Phao cạn chặn/ngắt. Quan sát và đo thực tế bơm có dừng sau 1 giây; timer chạy ở task riêng, không phải mạch ngắt phần cứng và không bảo đảm khi CPU treo/relay dính.
7. Lặp 3 lần với nghỉ >=10 giây, đo ml. `Q = tổng ml / tổng giây bơm đo thực tế`. Kiểm tra không tự chảy tiếp sau khi bơm tắt. Chưa bật Auto cho tới khi chọn xung/ngưỡng/nghỉ phù hợp cây và kiểm thử firmware vận hành.
8. Đóng Serial Monitor và thu log 30–60 phút:

```bash
python tools/capture_serial.py /dev/ttyUSB0 --output data/bench-2026-11-05.jsonl
```

Logger thêm giờ nhận trên laptop, không giả làm giờ đo. Đây là log bench 3 giây/mẫu, chưa đủ schema CSV huấn luyện (thiếu lịch sử tưới hoàn chỉnh). Không đưa trực tiếp vào train.

## 5. Phiếu ghi kết quả

| Hạng mục | Ghi thực tế |
|---|---|
| Board / relay / bơm / nguồn | |
| Relay kích LOW/HIGH, reset OFF | |
| Đất, cây, độ sâu cảm biến | |
| dry_raw / wet_raw | |
| DHT nhiệt độ / độ ẩm | |
| LDR che / sáng raw | |
| Phao đủ / cạn / rút dây | |
| Bơm lần 1 / 2 / 3: giây và ml | |
| Bơm OFF còn chảy nước? | |
| Đường dẫn log, lỗi gặp | |

## 6. Tiếp theo cho TV1 và điểm cần TV2

- Sau buổi lắp: chốt model/pin, chuyển driver đã đo kiểm vào adapter vận hành; tích hợp ngắt bơm, UTC, HTTP ở task riêng, ACK và nhật ký. Chưa nối bản bench vào lõi Auto.
- Ngày thu dữ liệu: thống nhất `docs/TV2_CONTRACT.md`, gửi 60 giây/mẫu, đo khoảng thiếu; TV2 cung cấp IP LAN máy backend, port, device ID, API key và endpoint nhận telemetry. ESP32 không gọi `localhost` của laptop. Không cần em gửi mật khẩu Wi-Fi vào chat; cấu hình local khi làm adapter mạng.
- Docker/PostgreSQL thuộc TV2; chỉ cần sẵn khi tích hợp HTTP. Hiện chưa có compose/backend trong repo này, chưa có API đang chạy.
- Sau có đủ chu kỳ khô–tưới: chạy pipeline AI hiện có, chia dữ liệu theo thời gian, so hai baseline, Linear Regression, Random Forest. Không dùng dữ liệu giả để báo cáo kết quả thực nghiệm.

Nguồn kỹ thuật: [Espressif ADC](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html), [ESP Timer v4.4](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32/api-reference/system/esp_timer.html). Pin map chỉ áp dụng cho board đã nêu, cần đối chiếu linh kiện nhận thực tế.

## Kiểm chứng phần mềm ngày 04/11/2026

- `pio run -d firmware -e bringup`: SUCCESS, Arduino-ESP32 2.0.17, RAM 21.832 byte, flash 292.517 byte. Chưa nạp lên board thật.
- Bộ kiểm thử native của controller: tất cả assertions đạt.
- Logger: đã thử qua pseudo-terminal, bỏ dòng lỗi, giữ null, thêm received_at và thoát Ctrl+C đúng.
- `python3 -m py_compile tools/capture_serial.py` và `git diff --check`: đạt.
- Chưa chạy lại bộ Python AI vì môi trường hệ thống thiếu pytest; không sửa mã AI trong đợt này.
- Chưa xác nhận số đo, mức kích relay, thời gian ngắt thật, lưu lượng hay tính tương thích linh kiện. Các mục này nghiệm thu bằng checklist khi nhận hàng.
