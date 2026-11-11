# W01 — xử lý phiên tưới ngày 11/11/2026

## Nguồn và phạm vi

Xuất trực tiếp PostgreSQL local trong transaction REPEATABLE READ READ ONLY, thiết bị garden-01, data_origin=real, theo received_at từ 12:13 ngày 11/11 đến trước ngày 12/11. Không sửa database, không dừng logger hoặc gửi lệnh thiết bị. Snapshot có mẫu đo từ **12:13:14 đến 21:03:46 giờ Việt Nam**, dài **8 giờ 50 phút 32 giây**; mẫu nhận cuối 21:03:49. Đây không phải xác nhận giờ ngắt USB.

Nhật ký theo ảnh người dùng: tưới tay 12:13–12:14, khoảng 4 muỗng cà phê, chưa đo ml. Người dùng xác nhận không tác động thêm; giữ volume_ml=null và actual_ms=null. Không dùng 30–35 ml/lần thử bơm trước đó để gán lượng nước cho phiên này. Giờ tưới chỉ chính xác đến phút. Mọi lần tưới trước phiên chưa biết; dữ liệu đầu phiên trước khi tưới kết thúc không dùng làm đặc trưng.

## Kết quả kiểm tra

| Chỉ tiêu | Kết quả |
|---|---|
| Mẫu xuất / chấp nhận | 1.062 / 1.062 |
| Trùng, xung đột, nhảy sequence, giờ lùi | Không phát hiện |
| Boot / calibration | 1 / soil-2511-979 |
| Chu kỳ mẫu | Trung vị 30 giây; min 29, max 31 |
| Độ trễ nhận | Trung vị 2,55 giây; max 11,71 giây |
| Mẫu soil/DHT invalid | 0 / 0 |
| Trạng thái | Toàn bộ OFF, không mẫu pump_on; không event bơm trong khoảng xuất |
| Tổng hợp | 530 phút đã khép; không thiếu phút |
| Loại khỏi đặc trưng | 2 phút tưới: 12:13 và 12:14 |
| Còn lại | 528 phút |
| Chỉ số đất | 0,98–26,11%; trung vị 4,11%; cuối 3,07% |
| Nhiệt độ | 30,9–32,7 °C |
| Độ ẩm không khí | 62,4–68,4% |

Dùng giờ đo trên ESP32, không thay bằng giờ nhận. Tổng hợp median, không nội suy, không điền mẫu thiếu. Phút cuối 21:03 chưa khép tại cutoff nên không đưa vào CSV AI. Cờ sensor valid chỉ xác nhận điều kiện phần mềm, không chứng minh độ chính xác vật lý.

## Những điểm cần đối chiếu

- Chỉ số đất tăng 0,98 → 19,45% tại 12:13:44; thêm đỉnh 26,11% tại 12:15:43 rồi giảm về 4,96% lúc 12:16:14. Giữ nguyên; chưa kết luận nguyên nhân. Khoảng đáp ứng sau tưới vẫn nằm trong CSV, cần đánh giá trước huấn luyện chính thức.
- Lúc 20:47:16 giảm 2,74 điểm phần trăm trong một mẫu. Người dùng xác nhận không tác động, nên không tự gán là tưới hay di chuyển cảm biến.
- Chỉ số đất phần lớn thấp, không giảm đơn điệu cả phiên. Đây là chỉ số hiệu chuẩn tương đối, không phải độ ẩm thể tích hoặc bằng chứng đất thật khô đến mức cụ thể.
- Ánh sáng có 367/1.062 mẫu ADC=4095; dấu hiệu chạm trần đo, chưa quy đổi lux. Model v2 hiện không dùng ánh sáng làm đặc trưng.

## Readiness AI

| Horizon | Cửa sổ hợp lệ | Train / validation / test sau purge |
|---|---:|---|
| 30 phút | 483 | 259 / 67 / 97 |
| 60 phút | 453 | 211 / 31 / 91 |

Cả hai đạt training_pipeline_ready=true, nhưng real_world_evidence_sufficient=false. Chưa huấn luyện/chọn model hoặc công bố MAE trong đợt xử lý này. Một chu kỳ liên tục không phải nhiều thí nghiệm độc lập. Cảnh báo chung trong assess về hiệu chuẩn/nhật ký xuất phát từ hai phút bị loại; không có thiếu phút truyền dữ liệu trong phiên.

Cần thu thêm các chu kỳ độc lập có nhật ký và kiểm tra phản ứng cảm biến trước khi đánh giá AI thật. Giữ can_trigger_pump=false.

## Tệp đầu ra

Trong `artifacts/session-2026-11-11/`:

- `database-rows.jsonl`: nguyên hàng database; `telemetry.jsonl`: payload nguồn kèm received_at.
- `pump-events.json`: event bơm trong phạm vi xuất (rỗng).
- `watering-journal.json`: nhật ký có nguồn và giới hạn độ chính xác.
- `prepared/`: CSV telemetry và báo cáo kiểm tra nguồn.
- `minute-data.csv`, `minute-data.quality.json`: lưới phút và chất lượng.
- `readiness-30m.json`, `readiness-60m.json`: kiểm tra đầu vào AI.
- `summary.json`, `soil-changes-review.csv`, `sensor-trends.png`: thống kê và điểm cần đối chiếu.
- `SHA256SUMS.txt`: checksum các tệp đầu ra.
