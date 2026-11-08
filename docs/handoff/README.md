# Bàn giao TV1 → TV2 — cập nhật 08/11/2026

Đây là gói mã nguồn và bằng chứng kiểm thử offline. Bringup đã thử bơm có giám sát; chưa nghiệm thu runtime ESP32 ↔ backend thật hoặc tưới tự động. Không chứa mật khẩu/API key hoặc mô hình được phép tự kích bơm.

Runtime telemetry-only đã đọc cảm biến, kết nối Wi-Fi, đồng bộ NTP và thu JSONL local trên thiết bị thật. [Phiên 01](../REAL_SESSION_01_2026-11-08.md) có 20 mẫu, 19 timestamp hợp lệ; chưa gửi thành công lên API. Chu kỳ telemetry hiện là **30 giây**, xem nhanh Serial là **3 giây**. Không dùng kết quả local để xác nhận PostgreSQL đã lưu.

Ưu tiên tích hợp đầu tiên là nhận/lưu/ACK telemetry và chống trùng; chưa mở điều khiển bơm. Xem [sơ đồ hệ thống](../SYSTEM_ARCHITECTURE.md) và [việc TV1 còn lại](../TV1_REMAINING_TASKS.md).

## TV2 bắt đầu từ đâu

1. Đọc `docs/TV2_CONTRACT.md` để triển khai endpoint và phản hồi ACK.
2. Đọc `docs/TV1_RUNTIME.md` để hiểu commissioning, retry và giới hạn.
3. Chạy mock/test; sau đó đối chiếu với FastAPI/PostgreSQL của nhóm.
4. Cung cấp cho TV1: URL LAN, device ID, API key riêng, CA nếu HTTPS, định dạng ACK đã thống nhất. Cấu hình bí mật chỉ trên máy local.

## Kiểm tra lại trên repo Smart-Green

```bash
cd /home/ad/Desktop/Smart-Green
bash tools/test_firmware.sh
.venv-ai/bin/python -m pytest -q ai/tests tools/tests
.venv-ai/bin/python -m pytest -q integration/test_http_runtime.py
```

Test integration cần quyền mở socket localhost và g++; tự tạo server ở port tạm rồi đóng. Dùng core/protocol C++ thật nhưng clock, sensor và storage là giả lập. Chưa kiểm thử FreeRTOS, Wi-Fi, NVS vật lý hoặc GPIO.

Các kịch bản: ACK lệnh thất bại rồi reboot/replay; server chậm; sự kiện đã lưu nhưng mất phản hồi; sai key/device/hết hạn; Auto không phụ thuộc server và chặn cạn nước.

## Thử endpoint mà không điều khiển thiết bị

Tại thư mục gốc repo, chỉ trỏ tới backend phát triển và device thử `SIM-ONLY`:

```bash
read -rsp 'Test API key: ' SG_TEST_KEY
export SG_TEST_KEY
curl --fail-with-body -H "X-API-Key: $SG_TEST_KEY" -H 'Content-Type: application/json' \
  --data-binary @docs/handoff/telemetry.synthetic.json \
  http://127.0.0.1:8000/api/v1/devices/SIM-ONLY/telemetry
curl --fail-with-body -H "X-API-Key: $SG_TEST_KEY" \
  'http://127.0.0.1:8000/api/v1/devices/SIM-ONLY/commands/next?after_seq=0'
```

Với mock, dùng cùng key và device thử:

```bash
SMART_GREEN_MOCK_KEY="$SG_TEST_KEY" python3 tools/mock_tv2.py --device SIM-ONLY --port 8000
```

Gửi telemetry hai lần phải chỉ có một identity; không tạo command WATER trong bước smoke test này. Mock chỉ giữ RAM, không thay database thật.

## Checklist tích hợp thật

- [ ] API key chỉ được ghi/đọc đúng device_id.
- [ ] Telemetry chống trùng theo device_id/boot_id/sample_seq; giữ null, timestamp và received_at riêng.
- [ ] Server chỉ ACK khi đã ghi bền; event trả đúng event_id.
- [ ] Lệnh có sequence bền vững, TTL tối đa 60s; GET next trả lệnh chưa ACK cũ nhất.
- [ ] ACK từ chối/duplicate cũng loại lệnh khỏi hàng chờ; duplicate không đồng nghĩa lần trước thành công.
- [ ] Event Reboot giữ actual_ms=null; không thay thành 0 hay suy lượng nước.
- [ ] Kiểm tra mất mạng/reset và đầy event queue 32 mục trên thiết bị.
- [ ] Hiệu chuẩn thực tế và đo giới hạn bơm trước mở commissioning.
- [ ] AI dùng cùng feature_version và calibration_id; can_trigger_pump vẫn false trước nghiệm thu.

## AI và database

`artifacts/ai-report-synthetic-2026-11-07/index.html` là báo cáo tự chứa biểu đồ. Nguồn là 10 ngày **giả lập**, không phải dataset cây thật. Có bảng MAE và dự đoán của bốn phương án; không báo số này như kết quả thực nghiệm.

PostgreSQL mới có script staging `db/import_bench.sql`, chưa dựng/chạy database. Backend/Web/DB production do TV2 phụ trách; cần thống nhất trước khi triển khai thêm container.

Kết quả và lệnh tạo lại báo cáo: [AI offline 07/11](../AI_OFFLINE_RESULTS_2026-11-07.md). Quy trình dữ liệu mới: [thu và kiểm tra telemetry](../TV1_DATA_COLLECTION.md).

## Bổ sung offline ngày 08/11/2026

- [Tích hợp AI v2](AI_INTEGRATION.md): schema CSV và hàm predict.
- [Nhật ký tưới / builder](../WATERING_AND_AI_DATASET.md): hỗ trợ tưới tay không giả thời gian bơm.
- [Nghiệm thu phần cứng](../TV1_HARDWARE_ACCEPTANCE.md): các ca còn cần thử thực tế.
