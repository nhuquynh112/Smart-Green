# Hợp đồng TV1–TV2 v0.2 (runtime adapter đã viết, chờ tích hợp)

TV1 đã viết adapter theo hợp đồng này và mock tại tools/mock_tv2.py. Backend thật chưa được nối kiểm chứng; hai bên cần thống nhất các phản hồi dưới đây.

## Telemetry

`POST /api/v1/devices/{device_id}/telemetry`, dự kiến mỗi 60 giây. Header `X-API-Key` riêng từng thiết bị; dùng HTTPS khi ra Internet. Server kiểm tra key có quyền với device_id và chỉ ACK sau khi ghi thành công. Thiết bị chưa đồng bộ giờ: timestamp=null; giữ boot_id/uptime để chẩn đoán, không tự lấy giờ nhận làm giờ đo cho AI.

```json
{
  "schema_version": 1,
  "device_id": "garden-01",
  "boot_id": "unique-per-boot",
  "sample_seq": 12,
  "timestamp": "2026-11-05T02:00:00Z",
  "uptime_ms": 720000,
  "calibration_id": "soil-01-v1",
  "data_origin": "real",
  "soil_raw": 2300,
  "soil_pct": 37.2,
  "temperature_c": 28.4,
  "humidity_pct": 68.0,
  "light_lux": null,
  "soil_valid": true,
  "air_valid": true,
  "tank_ok": true,
  "pump_on": false,
  "mode": "AUTO"
}
```

Giá trị trên chỉ minh họa schema, không phải số đo. Khóa chống trùng `(device_id,boot_id,sample_seq)`. Lưu `received_at` riêng với `timestamp`. Lỗi cảm biến gửi null + cờ false, không đổi lỗi thành số 0. Không có cảm biến lux thì null, không dùng số ADC LDR như lux.

## Lệnh

`GET /api/v1/devices/{device_id}/commands/next?after_seq=N` → 204 khi không có lệnh, 200 khi có một lệnh. Server cấp sequence tăng bền vững theo thiết bị, không tái dùng sau restart. Runtime hiện gọi `after_seq=0` và server trả lệnh có sequence nhỏ nhất chưa ACK: như vậy sau reset, lệnh đã thực thi nhưng mất ACK được gửi lại, core trả duplicate thay vì tưới lại. Sau ACK (kể cả từ chối), không trả lại lệnh đó. Firmware adapter phải kiểm tra kiểu, phạm vi, source và mode trước gọi core.

```json
{
  "schema_version": 1,
  "device_id": "garden-01",
  "command_seq": 42,
  "kind": "WATER",
  "source": "AI",
  "duration_ms": 2000,
  "issued_at": 1793844000,
  "expires_at": 1793844030
}
```

`issued_at/expires_at`: Unix UTC giây, TTL tối đa 60 giây. WATER không hợp lệ nếu quá giới hạn cấu hình. SET_MODE nhận OFF/MANUAL/AUTO. STOP hợp lệ tắt bơm và chuyển OFF. STOP hết hạn/trùng chỉ được dùng để dừng ngay, không được phép làm bơm bật. Lệnh AI chỉ hợp lệ trong AUTO và đất chưa quá aiCeiling. MANUAL vẫn chịu mọi giới hạn an toàn. Lệnh bị từ chối sau khi đã ghi sequence không được gửi lại với cùng sequence để mong thực thi.

Mất clock: không nhận lệnh bật. Mất mạng: core AUTO tiếp tục nếu đã có giờ hợp lệ và cảm biến an toàn; OFF giữ OFF. Mạng/HTTP phải chạy riêng, không chặn vòng kiểm tra bơm.

## Xác nhận và sự kiện

`POST /api/v1/devices/{device_id}/commands/{seq}/ack`: JSON gồm schema_version, device_id, command_seq, result. Trả 200 hoặc 204 sau khi lưu ACK. result có kết quả `started`, `stopped`, `mode_set`, `duplicate`, hoặc lý do từ chối của core. ACK `started` không đồng nghĩa tưới xong.

`POST /api/v1/devices/{device_id}/events`: gồm event_id, command_seq (0 nếu rule), started_at, planned_ms, actual_ms, source, reason. `(device_id,event_id)` duy nhất; nếu xóa NVS/đổi thiết bị phải tạo identity mới để không trùng. Server trả ACK id sau ghi bền; firmware gọi `acknowledgeEvent(id)` đúng thứ tự. `reason=Reboot` phải chuyển actual duration thành unknown/null khi xuất dữ liệu, không tự suy ra lượng nước.

TV2 tạo CSV AI từ telemetry **và** lịch sử tưới hoàn chỉnh. `water_total_ms` là bộ đếm cộng dồn thời gian bơm đã thực hiện, không phải quota dự trù và không reset hằng ngày. Nếu có sự kiện không rõ thời gian, đánh dấu khoảng không hợp lệ; không tạo số 0 giả. Đến khi adapter đầy đủ, sử dụng synthetic fixture để thử backend, gắn nhãn rõ.

## Giao diện AI trong Python

```python
from smart_green_ai.inference import predict
advice = predict(trusted_bundle, recent_minute_dataframe, now="2026-11-05T02:01:00Z")
```

`recent_minute_dataframe` theo DATA_AND_AI.md. Hàm trả độ ẩm dự đoán, horizon, as_of, model, điều kiện không tưới thêm và `can_trigger_pump=False`. TV2 không tự đổi thành true. Chỉ mở tính năng tạo lệnh AI sau nghiệm thu dữ liệu thật và đường điều khiển; khi mô hình lỗi dùng Auto-Rule, không suy diễn tưới từ lỗi.


## Chi tiết adapter 06/11/2026

- Telemetry: HTTP 2xx chỉ sau khi lưu bền; request lặp cùng identity cần idempotent. Cùng identity nhưng payload xung đột phải báo lỗi, không ghi đè âm thầm.
- Event: trả JSON `{ "event_id": N }` cùng mã 2xx chỉ sau khi lưu bền. Firmware chỉ xóa event tương ứng khỏi NVS khi nhận đúng id. Reason có thêm Guard; actual_ms đo thời gian GPIO bật, Reboot là null.
- ACK gồm `result`; có thể nhận `ai_disabled`, `invalid_*`, `output_fault`, hoặc lỗi core ngoài các kết quả đã liệt kê. ACK `duplicate` sau reboot không tự khẳng định lần thực thi trước thành công; đối chiếu event.command_seq.
- HTTP response tối đa 4096 byte; không redirect. HTTPS cần CA; HTTP chỉ opt-in cho LAN phát triển. API key phải được gắn quyền đúng device_id phía server.
- Telemetry bổ sung build_stage, commissioned, storage_fault, clock_ready, clock_fault, server_available, last_command_seq, queued_events, telemetry_overwrites, light_raw. Giá trị lux vẫn null với LDR.
- Timestamp là lúc task cảm biến đọc xong; nhiệt/ẩm DHT có thể cũ hơn vài giây. Dữ liệu stale bị đặt null/cờ false. received_at do backend ghi, không dùng thay timestamp tự động.
- Mất mạng: telemetry có thể thiếu do queue hữu hạn, event lưu bền tối đa 32. Không nội suy giả thời gian tưới khi reason=Reboot.

Xem TV1_RUNTIME.md để biết cấu hình, giới hạn và trạng thái nghiệm thu.
