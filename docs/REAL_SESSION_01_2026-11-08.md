# Phiên thu thật 01 — 08/11/2026

## Phần đã xác minh

Nguồn: `firmware/data/telemetry-session01.jsonl`, SHA256 `f7bfe3084bca1cdbc7cd438ce6dc601b35f17c61ce050b5ee03f6f441d17949b`.

| Chỉ số | Kết quả |
| --- | --- |
| Thiết bị / hiệu chuẩn | garden-01 / soil-2511-979 |
| Số mẫu hợp lệ | 20 |
| Bản trùng / bản từ chối ở parser | 0 / 0 |
| Phiên boot / lỗi sequence | 1 / 0 |
| Chu kỳ mẫu có giờ đo | 29–31 giây |
| Giờ đo hợp lệ | 19 mẫu; mẫu số 1 chưa có NTP nên null |
| Giờ nhận | Có đủ 20 mẫu |
| Khoảng giờ đo đã ghi (giờ Việt Nam) | 12:00:24–12:09:25 ngày 08/11/2026 |
| Độ ẩm đất tương đối | 24,15–24,80%; cả 20 mẫu soil_valid=true |
| Bơm | OFF toàn phiên |
| Gói gửi server thành công | 0; chưa có API TV2 |

Wi-Fi và đồng bộ thời gian đã hoạt động trên runtime thật. Firmware đã sửa lỗi timestamp không được tạo trong JSON; null trước NTP được giữ nguyên. Không dùng giờ nhận để lấp giờ đo còn thiếu. Dòng Serial `# live` không phải JSON, nên bộ thu bỏ qua; không diễn giải số dòng bỏ qua là số mẫu cảm biến bị mất.

Đây là phép kiểm tra thu dữ liệu local, **chưa hoàn tất luồng ESP32 → API → PostgreSQL** và không phải nghiệm thu điều khiển bơm.

## Đánh giá khả năng huấn luyện

Kết quả `telemetry-session01.ai-readiness.json`: `training_pipeline_ready=false`. CSV raw còn thiếu `minutes_since_water`, `water_event_count`; một mẫu chưa có giờ đo. Phiên khoảng 10 phút cũng chưa đủ để tạo cửa sổ 15 phút lịch sử + 30 phút dự báo, càng chưa đủ nhiều chu kỳ độc lập.

Đã tạo `firmware/data/watering-session01.json` làm nhật ký nháp. `history_complete=false`, thời điểm tưới trước phiên null, danh sách events rỗng chưa có nghĩa không tưới. Không tự suy ra tưới tay từ pump_on=false. Người quan sát cần điền lịch sử có thật; không nhớ thì giữ thiếu và không train trên phần đó.

## Việc tiếp tục không cần TV2

1. Thu phiên dài hơn vào file mới, giữ cảm biến cố định và không thay cấu hình hiệu chuẩn giữa phiên.
2. Ghi lại mọi lần tưới tay, thời điểm bắt đầu/kết thúc và lượng nước nếu đo được. Ghi cả thay đổi cảm biến/chậu/reset.
3. Theo dõi nhiều chu kỳ khô–tưới, không tưới hoặc làm khô cây chỉ để ép đủ mẫu cho mô hình.
4. Sau phiên, chạy parser rồi tổng hợp theo [nhật ký và CSV AI](WATERING_AND_AI_DATASET.md). Chỉ xác nhận lịch sử đầy đủ khi có căn cứ.

Chạy thử phiên tiếp theo 1 giờ (đóng mọi Serial Monitor trước; cổng hiện tại là `/dev/ttyUSB1`):

```bash
cd ~/Desktop/Smart-Green
/home/ad/.platformio/penv/bin/python tools/capture_serial.py /dev/ttyUSB1 --seconds 3600 --output firmware/data/telemetry-session02.jsonl
python3 firmware/tool/parse_logs.py firmware/data/telemetry-session02.jsonl --output firmware/data/prepared/telemetry-session02.csv
```

Lệnh thứ hai chỉ chạy sau khi logger kết thúc. Không bấm EN hoặc để máy ngủ trong lúc thu. File logger ghi nối tiếp: dùng tên phiên mới nếu đã có session02. Chưa tự khởi chạy phiên này trong lúc soạn báo cáo; người dùng chọn lúc thiết bị sẵn sàng.

## Việc chờ TV2

URL/API key/device ID, nhận và lưu telemetry PostgreSQL, ACK sau lưu bền, chống trùng, đối chiếu DB, thử mất mạng/phục hồi cùng backend thật. Cho tới đó http=-1/telemetry_sent=0 không chứng minh cảm biến hoặc Wi-Fi bị hỏng.
