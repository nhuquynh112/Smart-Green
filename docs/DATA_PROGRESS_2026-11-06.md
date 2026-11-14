# Tiến độ pipeline dữ liệu — 06/11/2026

## Đã kiểm chứng

- Giữ nguyên firmware, script `firmware/tool/parse_logs.py` và file CSV 25 dòng ban đầu.
- Phiên Serial mới có 13 mẫu, từ 12:20:49 đến 12:21:25 giờ Việt Nam (khoảng 36 giây giữa mẫu đầu/cuối). Không phải phiên thu đủ 2 phút; đã dừng theo yêu cầu người dùng.
- 13/13 có `received_at` UTC, không trùng identity, không mất sequence giữa các mẫu, một boot_id; bơm báo OFF toàn phiên.
- Đất raw 2553–2558; DHT22 32.5°C, độ ẩm 65.8–66%; LDR raw 960–966. Đây là số đo DHT22, không phải nhiệt độ chip ESP32.
- Đất chưa hiệu chuẩn: giữ soil_pct=null, soil_valid=false, dry_raw=wet_raw=-1.
- Log cũ: 25 dòng giữ lại, 1 dòng lỗi, thiếu sequence 16. Không bổ sung giờ nhận giả cho dữ liệu cũ.
- Đã đóng phiên thu. Các thao tác xử lý tiếp theo không cần board cắm USB.

## File và cách chạy lại

Từ `/home/ad/Desktop/Smart-Green`:

```bash
python3 tools/prepare_telemetry.py firmware/data/bench_received_session_03.jsonl --output-dir firmware/data/prepared
python3 tools/prepare_telemetry.py firmware/logs/device-monitor-261106-115014.log --output-dir firmware/data/prepared
python3 -m unittest discover -s tools/tests -v
```

Mỗi nguồn sinh ba file theo tên nguồn: `.csv` để đọc, `.quality.json` để xem lỗi/thiếu/trùng/đồng hồ, `.postgres.csv` để nhập staging. Chạy lại sẽ thay các file dẫn xuất cùng tên; nguồn gốc giữ nguyên. Công cụ này kiểm tra schema bench hiện tại, không phải validator API production.

Khóa chống trùng là `(device_id, boot_id, sample_seq)`. Bản ghi cùng identity nhưng khác payload bị báo lỗi và giữ bản đầu. Bản lặp chỉ khác received_at giữ lần nhận đầu. Không tự nội suy, điền số 0 hay sửa thứ tự đồng hồ.

Năm kiểm thử đã đạt: JSON lỗi/trùng/mất mẫu, identity xung đột, sai kiểu/NaN/giờ thiếu timezone, reset tạo phiên mới, đồng hồ nhận không tăng. CSV PostgreSQL đã được đọc lại để xác nhận payload nguyên vẹn.

## Giờ nhận và thu liên tục

`received_at` là lúc laptop đọc được khối byte chứa dòng JSON hoàn chỉnh. Nó phụ thuộc đồng hồ máy và có độ trễ/buffering; không phải giờ đo chính xác trên ESP32. `timestamp` vẫn null. Không dùng received_at âm thầm thay timestamp trong pipeline AI hiện tại.

Công cụ `tools/capture_serial.py` đã đặt DTR/RTS false trước khi mở cổng và đọc theo khối byte, giữ dữ liệu phân mảnh, giới hạn bộ đệm dòng lỗi. Kiểm tra thực tế đã thu được 13 mẫu; chưa có bằng chứng chạy ổn định dài hạn. Mở cổng có thể reset board.

Chỉ chạy lệnh sau khi đã chủ động cắm thiết bị và đóng monitor:

```bash
/home/ad/.platformio/penv/bin/python tools/capture_serial.py /dev/ttyUSB0 --seconds 60 --output firmware/data/new_session.jsonl
```

Bỏ `--seconds 60` để thu liên tục; Ctrl+C dừng. Nên đặt tên file riêng cho đợt mới; logger ghi nối nếu file đã tồn tại. Kiểm tra đồng hồ laptop trước khi thu dài hạn. Cần đo kiểm riêng nếu board nóng bất thường; phần mềm không đo nhiệt độ board.

## PostgreSQL / Docker — chuẩn bị, chưa triển khai

Repo chưa có backend hay Compose. Đã chuẩn bị `db/import_bench.sql` và CSV staging; chưa chạy SQL trên PostgreSQL thật và chưa dựng container Docker. Đây là schema `bench` riêng để thử nhập, không thay kiến trúc/database TV2.

Khi TV2 đã có database phát triển, chạy từ thư mục gốc repo:

```bash
psql "$DATABASE_URL" -f db/import_bench.sql
```

`DATABASE_URL` phải được cấu hình local tới database phát triển đúng; không gửi mật khẩu vào chat hoặc commit Git. Nếu chạy psql trong container phải mount file CSV tương ứng; lệnh trên dùng psql ở máy host kết nối PostgreSQL (có thể nằm trong Docker).

SQL nhập giao dịch, rollback khi lỗi, giữ timestamp và received_at riêng, dùng primary key chống nhập trùng; báo lỗi khi identity đã tồn tại nhưng payload khác. Chưa có HTTP/API, tài khoản web hoặc lịch sử tưới production trong phần bổ sung này.

## Bước tiếp theo còn phụ thuộc thực tế

1. Hiệu chuẩn đất thật; kiểm tra relay và bơm theo checklist riêng.
2. Thống nhất PostgreSQL/backend đang dùng của TV2 trước khi dựng thêm môi trường.
3. Thu dài hạn nhiều chu kỳ khô–tưới, giữ lịch sử tưới và phiên hiệu chuẩn.
4. Chốt chính sách thời gian đo/đồng bộ UTC rồi tạo CSV AI theo DATA_AND_AI.md.

13 mẫu mới và 25 mẫu cũ chỉ chứng minh đường thu dữ liệu. Chưa đủ huấn luyện/đánh giá AI và chưa bật tưới tự động.
