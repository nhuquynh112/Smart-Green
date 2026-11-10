# Tích hợp ESP32 → FastAPI → PostgreSQL, 09/11/2026

**Cập nhật:** database hiện chạy bằng Docker, xem [hướng dẫn PostgreSQL và pgAdmin](LOCAL_DATABASE.md). Cấu hình Unix socket bên dưới là bằng chứng của phiên trước khi chuyển.

Đã xác minh đường truyền trên thiết bị thật lúc 11:09–11:11 giờ Việt Nam. Backend TV2 đã được gộp tại commit dadf068; không còn chờ triển khai endpoint telemetry.

## Cấu hình đã chạy

- ESP32 qua `/dev/ttyUSB0`, device `garden-01`, calibration `soil-2511-979`.
- Backend LAN: `http://<BACKEND_LAN_IP>:8000`; endpoint `POST /api/v1/devices/garden-01/telemetry`.
- Xác thực bằng header `X-API-Key`; key riêng được lưu local, không ghi vào tài liệu/Git. Thử key sai nhận 401, key đúng được chấp nhận.
- PostgreSQL 16 riêng của dự án, database `smart_green_local`, Unix socket `artifacts/backend-local/socket`, port 55432; không dùng SQLite và không sửa cluster hệ thống.
- Firmware `runtime_telemetry_only`, `SG_TELEMETRY_ONLY=true`, `SG_AI_COMMANDS_ENABLED=false`; mode OFF, bơm bị khóa.
- Lần nạp đầu 115200 baud mất phản hồi giữa chừng. Nạp lại 57600 baud thành công, hash flash được xác minh.

## Bằng chứng

File local (gitignored): `artifacts/backend-local/telemetry-first.jsonl`, `capture-first.log`, `verification.json`.

- Boot được đối chiếu: `abe8bac3db566a4e`, sample_seq 1–4.
- Cả 4 payload serial khớp hoàn toàn payload trong PostgreSQL, sau khi bỏ thời điểm nhận do logger thêm.
- Có 3 mẫu có giờ đo UTC hợp lệ; mẫu đầu chưa đồng bộ NTP giữ timestamp null.
- Mẫu cuối đo lúc 11:10:50: soil 13.44648%, nhiệt độ 32.1°C, độ ẩm không khí 57.9%, tank_ok=true.
- Mẫu cuối báo HTTP 200, telemetry_sent=3, telemetry_failures=0, server_available=true. Bộ đếm gửi nằm trong payload trước khi gửi chính mẫu đó; database đã có đủ 4 mẫu.
- Cả 4 mẫu: pump_on=false, telemetry_only=true; không có storage_fault/clock_fault.
- Database có tổng cộng 5 mẫu tại lúc kiểm tra: 4 mẫu của phiên đối chiếu và 1 mẫu từ boot trước khi mở logger.
- SHA256 serial: `aae5a4b381fc6bd4fb2273215b22128c59b7b7e04ed3b68553b12aa752e26cc4`.

Đây là xác minh đường truyền và lưu trữ trong phiên ngắn. Đã bổ sung thử backend không phản hồi và phục hồi bên dưới; chưa thử ngắt Wi-Fi/router, chưa nghiệm thu tưới hoặc AI trên dữ liệu thật. Các giá trị độ ẩm không tự chứng minh nhu cầu tưới.

## Chạy lại trên máy này

Giữ máy và ESP32 trong cùng LAN. IP trên là IP hiện tại; nếu DHCP đổi IP, cập nhật cả cấu hình firmware và địa chỉ bind backend rồi nạp lại.

Nếu PostgreSQL riêng đang tắt, chạy từ thư mục gốc repo:

```bash
/usr/lib/postgresql/16/bin/pg_ctl -D artifacts/backend-local/pgdata \
  -l artifacts/backend-local/postgres.log \
  -o "-k <PROJECT_ROOT>/artifacts/backend-local/socket -p 55432 -h ''" start
```

Nếu backend đang tắt:

```bash
.venv-ai/bin/python artifacts/backend-local/run_backend.py
```

Cấu hình riêng nằm ở `artifacts/backend-local/runtime-env.json` (quyền 0600); firmware ở `firmware/include/site_config.h` (gitignored). Không đưa các file này vào Git. HTTP LAN chỉ dùng cho phiên thử cục bộ này. Backend và database hiện chạy trên laptop, chưa phải dịch vụ tự khởi động sau reboot.

## Thử backend không phản hồi và phục hồi — 11:21–11:24

Tạm dừng tiến trình backend bằng SIGSTOP trong 70.048 giây, sau đó SIGCONT. PostgreSQL và Wi-Fi vẫn hoạt động; đây không phải thử ngắt Wi-Fi hoặc khởi động lại server.

- Log: `artifacts/backend-local/outage-2026-11-09/`, gồm serial raw, telemetry JSONL, events và verification.
- Boot `d8c2f130b3f0978b`, 6 mẫu liên tiếp (seq 1–6), không reboot trong phiên.
- Khi backend dừng: cảm biến tiếp tục hợp lệ; HTTP -11, bộ đếm lỗi gửi tăng đến 19; server_available chuyển false.
- Sau phục hồi: seq 5 và 6 báo HTTP 200, server_available=true; số lỗi gửi không tăng thêm.
- Bơm OFF và telemetry_only=true trong cả 6 mẫu.
- PostgreSQL có seq 1, 2, 4, 5, 6; payload khớp serial. **Thiếu seq 3**, tương ứng telemetry_overwrites=1: hàng đợi telemetry giữ mẫu mới nhất, không phải bộ lưu trữ offline đầy đủ. Không nội suy hoặc tạo bản ghi thay thế.
- SHA256 telemetry: `297cdce096fa05fdd641e93c23d0b92228dd43d338f6efabb6a811f3a41baa6d`.

Kết luận: đã chứng minh tự phục hồi sau server không phản hồi và giữ bơm OFF. Chưa bảo đảm không mất dữ liệu khi offline; cần quyết định yêu cầu lưu đủ mẫu và thử mất Wi-Fi riêng trước khi chốt toàn bộ ca mất mạng.

## Mở database trên máy

Tên thư mục và database đã đổi theo chức năng; bản sao lưu trước khi đổi nằm tại `artifacts/backend-local/before-rename.dump`. Dữ liệu được giữ nguyên. Đổi tên cần dừng dịch vụ ngắn, không tính lần bảo trì này vào phiên kiểm thử mất kết nối ở trên.

Mở Terminal rồi chạy:

```bash
psql -h "<PROJECT_ROOT>/artifacts/backend-local/socket" -p 55432 -U ad -d smart_green_local
```

Xem mẫu mới nhất:

```sql
SELECT device_id, sample_seq, measured_at, soil_pct, temperature_c, humidity_pct, pump_running
FROM telemetry ORDER BY received_at DESC LIMIT 10;
```

Dùng `\dt` để liệt kê bảng, `\watch 5` để lặp lại truy vấn mỗi 5 giây, Ctrl+C để dừng lặp, `\q` để thoát.
