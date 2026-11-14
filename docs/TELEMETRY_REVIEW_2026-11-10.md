# Kiểm tra phiên thu telemetry — 10/11/2026

## Phạm vi và nguồn

Snapshot đọc từ PostgreSQL Docker, bảng telemetry, device garden-01. Chọn cửa sổ nhận dữ liệu một giờ: **14:10:52.771946 ≤ received_at < 15:10:52.771946**, giờ Việt Nam. Không dừng backend/ESP32, không sửa/xóa bản ghi nguồn; hệ thống có thể tiếp tục thu sau cửa sổ này.

Artifact local, gitignored: `artifacts/telemetry-review-2026-11-10/` gồm `database-rows.json`, `telemetry.jsonl`, `telemetry-quality.json`, `summary.json`, `watering-journal.json`, `minutes.csv`, `minutes-quality.json` và script xuất/kiểm tra. Bản JSONL dùng payload gốc kèm received_at của server PostgreSQL; đây không phải thời gian logger USB.

SHA256 JSONL: `8116844926b4f618558134859f0039e2ac3a4ed597f31633850fd973843ae969`.

## Kết quả

| Chỉ số | Kết quả |
|---|---|
| Số mẫu / parser chấp nhận | 122 / 122 |
| Mẫu trùng parser / mẫu bị từ chối | 0 / 0 |
| Boot | Một boot, không thấy reset trong snapshot |
| Sequence | 1–123, thiếu seq 2 |
| Timestamp | 121 hợp lệ; seq 1 null, clock_ready=false |
| Giờ đo hợp lệ đầu–cuối | 14:10:44–15:10:44 |
| Khoảng cách mẫu có giờ đo | 29–31 giây, trung vị 30 giây |
| soil_valid / air_valid | true trong cả 122 mẫu; chỉ là kiểm tra hợp lệ của firmware, không chứng minh độ chính xác hiệu chuẩn |
| Bơm / profile | pump_on=false, telemetry_only=true trong cả phiên |
| Phao | tank_ok=false trong cả 122 mẫu |
| Lỗi storage / clock | Không thấy cờ lỗi |
| Độ ẩm đất tương đối | 2.219321–10.57441%; cuối phiên 9.464752% |
| Nhiệt độ | 32.8–33.0°C |
| Độ ẩm không khí | 66.3–67.5% |
| Ánh sáng | ADC raw 1776–3278; lux=null vì chưa quy đổi |
| Sự kiện tưới nhận trong cửa sổ | 0; không dùng điều này thay nhật ký tưới tay |

Số mẫu 122 thay vì 120 không tự chứng minh dư/trùng: cửa sổ chọn theo giờ server nhận, có mẫu đầu chưa có giờ đo và mẫu tồn được gửi bù. Không suy thời điểm đo cho seq 1, không tạo seq 2.

Bộ đếm telemetry_failures là số lần gửi thất bại theo boot, không phải số mẫu mất: seq 3 báo 27, seq 4 báo 30, seq 31 báo 31, sau đó không tăng trong snapshot. telemetry_overwrites tăng tới 1 ngay đầu phiên và giữ nguyên. Seq 3–123 liên tiếp trong database, không thấy mất thêm mẫu sau giai đoạn đầu.

## Biến động cần kiểm tra

Lúc **14:19:15**, từ seq 19 sang 20, soil_pct tăng **2.415143 → 10.11749**. Người dùng sau đó đính chính: đã **cắm cảm biến đất sâu hơn khoảng 14:19**, không nhớ thời điểm chính xác; vẫn xác nhận không tưới. Thời gian thao tác phù hợp với bước nhảy số đo, có thể giải thích biến động nhưng không coi là chứng minh độc lập nguyên nhân. Giữ nguyên raw, không gắn nhãn tưới. Đánh dấu đây là thay đổi điều kiện đo, tách đoạn trước/sau thao tác khi phân tích; không coi cả phiên là một chuỗi khô tự nhiên không bị tác động. Nhật ký bổ sung: `sensor-interventions.json` trong thư mục artifact của phiên.

Phao báo không đủ nước xuyên suốt. Chưa kết luận bình thực sự cạn hay do vị trí/đấu dây/logic phao; cần đối chiếu trạng thái thực tế trước bất kỳ nghiệm thu tưới nào. Tiếp tục giữ bơm OFF.

## Nhật ký và khả năng dùng cho AI

- Người dùng xác nhận không tưới; có cắm cảm biến sâu hơn khoảng 14:19 (đính chính thông tin ban đầu “không tác động”). Giờ thao tác là ước lượng, khác với giờ mẫu đo 14:19:15 được ghi chính xác trong telemetry.
- Trước phiên, người dùng báo chưa tưới kể từ thứ Bảy, nhưng không có thời điểm tưới cuối chính xác. `last_watered_at_before_start=null`, không tự quy về một giờ bất kỳ.
- history_complete=true chỉ áp dụng cho xác nhận không tưới trong khoảng phủ nhật ký của phiên; không xác nhận toàn bộ lịch sử từ trước đó và không cập nhật cờ database.
- Builder tạo 60 phút đã đóng theo giờ đo, loại mẫu thiếu timestamp và không dùng phút cuối đang mở tại cutoff.
- Cả 60 phút chưa đủ điều kiện AI v2 do `unknown_previous_watering`; phút đầu còn `outside_journal_coverage` vì nhật ký bắt đầu tại giờ đo đầu thay vì đầu phút.
- Các điều kiện này không làm mất giá trị kiểm tra truyền dữ liệu/cảm biến của raw. Không huấn luyện model hoặc mở quyền AI kích bơm ở bước này.

## Việc tiếp theo

1. Sau phiên, đối chiếu trạng thái bình/phao và kiểm tra cố định, tiếp xúc, cấp nguồn của cảm biến đất; ghi thời điểm mọi điều chỉnh, không sửa raw cũ.
2. Những lần chăm cây sau ghi giờ tưới bắt đầu/kết thúc có thật, lượng nước nếu biết; không tưới chỉ để tạo nhãn.
3. Thu nhiều chu kỳ tự nhiên sau khi xác minh cảm biến. Tách phiên và lưu calibration khi thay đổi hiệu chuẩn/vị trí.

Kết luận: đã thu và lưu được cửa sổ một giờ, không thấy bơm bật/reset; chưa thể coi cảm biến đã được xác minh chính xác hoặc dataset đã sẵn sàng huấn luyện AI.
