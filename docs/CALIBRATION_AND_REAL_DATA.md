# Hiệu chuẩn và bắt đầu thu dữ liệu thật — 07/11/2026

Không cần hoàn thành relay/bơm để bắt đầu ghi cảm biến. Cần hiệu chuẩn đất, cố định cảm biến và giữ nhật ký tưới. Chưa dùng raw ngoài không khí làm mốc đất khô.

## Công cụ hiệu chuẩn

`tools/calibration.py` nhận số đo do người thực hiện cung cấp, không điều khiển bơm. File trắng đã tạo: `data/calibration-measurements-blank.json`.

- Ghi device/calibration ID, thời gian có timezone, loại cây/đất, độ sâu.
- Lấy ít nhất 5 mẫu raw ổn định cho mỗi mốc đất khô và đất ướt đã thoát nước; cùng vị trí/độ sâu. Trong bringup có lệnh dry/wet lưu mốc NVS, nhưng hồ sơ đo vẫn cần lưu riêng.
- Khi bơm đã được kiểm tra an toàn, ghi ít nhất 3 lần thử: thời gian thực tế và ml đong được, điện áp, ống và độ cao nâng. Không kéo dài thử bơm chỉ để đủ lượng nước.
- Chưa có bơm: để phần pump chưa điền; chưa chạy phân tích hồ sơ đầy đủ. Vẫn có thể hiệu chuẩn đất và ghi dữ liệu riêng bằng bringup.

Sau khi có đầy đủ số đo, lưu bản mới rồi chạy:

```bash
python3 tools/calibration.py analyze data/calibration-measurements-real.json --output-dir data/calibration-real-v1
```

Thư mục đầu ra phải chưa tồn tại để giữ lịch sử. Kết quả: bản sao measurements, report với lưu lượng/độ phân tán và `site_config.draft.h`. Draft giữ mọi cờ xác nhận false; không tự sửa cấu hình runtime. Các ước lượng thời gian theo thể tích không phải giới hạn an toàn được phê duyệt.

Có fixture `tests/fixtures/calibration_synthetic.json` để thử phần mềm, **không chép số của fixture vào mạch thật**.

## Thu dữ liệu thật đầu tiên

1. Hiệu chuẩn đất, giữ cảm biến ở vị trí cố định; không đổi chậu/đất mà giữ nguyên calibration ID.
2. Kiểm tra đồng hồ laptop. Đóng monitor trước khi mở logger, chỉ một chương trình sử dụng cổng.
3. Thu một phút để kiểm tra trước khi để ghi dài hạn:

```bash
/home/ad/.platformio/penv/bin/python tools/capture_serial.py /dev/ttyUSB0 --seconds 60 --output firmware/data/real-2026-11-07-session01.jsonl
```

4. Kiểm tra soil_pct khác null sau hiệu chuẩn, air_valid=true, received_at có timezone; ghi lại boot/reset và khoảng thiếu. `timestamp` trong bringup vẫn null. Giờ nhận laptop phải được giữ riêng; bước chuẩn hóa thời gian cho AI cần chốt theo phiên thu, không tự coi đó là giờ đo.
5. Ghi mọi lần tưới bằng nhật ký: timestamp có timezone, calibration_id, method (hand/pump), ml đo được nếu biết, thời gian chạy bơm thực tế nếu dùng bơm, ghi chú. Không biết thì null, không điền 0.
6. Với tưới tay, dùng [nhật ký tưới và builder AI v2](WATERING_AND_AI_DATASET.md). Bộ đếm sự kiện thay thời gian bơm để lọc cửa sổ; không giả actual_ms. Chỉ xác nhận lịch sử đầy đủ sau khi đối chiếu phiên quan sát.
7. Thu qua nhiều chu kỳ khô–tưới, không ấn định một số ngày là chắc chắn đủ. Chưa dùng 13/25 mẫu bench hay fixture synthetic như dataset nghiệm thu.

Nếu thiết bị nóng bất thường, dừng và kiểm tra nguồn/mạch. DHT22 không đo nhiệt độ chip ESP32.
