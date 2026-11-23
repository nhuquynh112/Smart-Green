# W07 — xử lý ngày 23/11/2026

## Kết quả

Đã đọc PostgreSQL bằng REPEATABLE READ READ ONLY. Session `f7f4a3da2d80552f9c439d21e97479cc`, tên w07, revision 5, active=0, history_complete=true. Không còn session active tại thời điểm kiểm tra. Không sửa nhật ký DB, telemetry, mô hình hay firmware.

Giờ Việt Nam: bắt đầu **21/11/2026 11:57:23**, kết thúc **19:23:36**, dài **7h26m13s** (không phải 8h). Có **868 bản ghi** real, cùng calibration soil-2511-979.

- Mẫu nhận đầu 12:09:54.572323: chưa đồng bộ đồng hồ, measured_at=null. Giữ nguyên trong raw, không suy diễn giờ đo.
- Mẫu có giờ đo: 12:10:20–19:23:22, dài 7h13m02s. Server nhận cuối 19:23:23.864539.
- Đầu phiên không có telemetry từ 11:57:23 đến 12:09:54 (khoảng 12m32s); đây là gián đoạn đã biết, không nội suy. Firmware được nạp lại khoảng 12:09 theo nhật ký.
- Sau phục hồi chỉ một boot e9144e9ebc3d55c8, sequence liên tục, không trùng khóa/timestamp hợp lệ, không timestamp ngược, không gap >90s. Nhịp đo 29–31s (trung vị 30); nhịp nhận 21.343–36.817s. Không thấy reset thêm trong dữ liệu, không khẳng định mọi gián đoạn Wi-Fi rất ngắn đều quan sát được.
- Đất 18.407–23.303%, nhiệt độ 32.4–33.2°C, độ ẩm không khí 58.2–66.5%. Toàn bộ mẫu soil_valid/air_valid=true, không thiếu hoặc vượt miền vật lý theo pipeline.
- Ánh sáng 639–4095 ADC; **75/868 = 8.64%** bão hòa 4095. Giữ raw, không chuyển thành lux, cần đánh giá độ nhạy loại bão hòa khi thử mô hình ánh sáng.
- Tất cả OFF, pump_running=false, clock_fault/storage_fault=false, queued_events=0, telemetry_overwrites=0. Không lệnh điều khiển hoặc watering_event giao thời gian phiên.

## Nhật ký

Người dùng xác nhận ngày 23/11: không tưới, di chuyển hoặc có tác động/reset nào thêm sau lần nạp firmware đầu phiên. Lưu nguyên xác nhận tại user-confirmations.json, không sửa lịch sử snapshot DB. Nhật ký DB đã đánh dấu đối soát nhưng câu ghi chú cũ vẫn nói kế hoạch chưa xác nhận; xác nhận mới là bằng chứng bổ sung.

**Giờ tưới cây gần nhất trước W07 vẫn chưa rõ.** Không lấy lần thử bơm hứng riêng làm lần tưới chậu. Không suy ra thời điểm tưới từ % độ ẩm. Chưa xác minh lịch sử giữa các phiên để khẳng định chu kỳ tưới độc lập.

## Điều kiện AI

Đã chạy pipeline hiện có `build_ai_dataset.build` và `light_supervised`, dùng giờ đo thiết bị và chỉ phút đã đóng, không train/model evaluation:

| Horizon | Cửa sổ hợp lệ không sáng / có sáng | Ứng viên chỉ xét cảm biến |
|---|---:|---:|
| 30 phút | 0 / 0 | 388 |
| 60 phút | 0 / 0 | 358 |

433 phút đóng từ 12:10–19:22. Thiếu last_watered_at_before_start khiến tất cả bị loại unknown_previous_watering. 388/358 chỉ kiểm tra chuỗi cảm biến đủ 16 phút lịch sử + horizon, bao gồm ADC bão hòa hợp lệ trong miền; không phải cửa sổ được phê duyệt train/test. Không đưa phút thiếu timestamp hoặc khoảng đầu offline vào đặc trưng, không bù dữ liệu.

W07 hữu ích cho theo dõi đất khô ở dải ~18–23%, khác dải W06 ~38–52%; chưa thể gán sự khác biệt hoàn toàn cho khô tự nhiên nếu chưa xác minh thời gian giữa phiên và vị trí đầu dò. Giữ W06/W07 cùng nhóm cho tới khi xác minh chu kỳ, tránh coi hai phiên là hai chu kỳ độc lập.

Cần bổ sung giờ tưới thực tế trước phiên nếu biết. Nếu không biết, giữ trạng thái unknown và dùng W07 cho phân tích cảm biến; nghiên cứu mô hình không cần minutes_since_water là nhiệm vụ riêng, không tự thay pipeline/model đang dùng để mở khóa.

## Tệp / kiểm tra

- database-rows.jsonl: snapshot đầy đủ, received_at >= start và < end, real garden-01.
- telemetry.jsonl: tên trường chuẩn hóa tương thích W05, giữ số đo; measured_at→timestamp, pump_running→pump_on.
- journal.json, session*.json: nhật ký và các revision gốc.
- watering-events.json gồm cả lịch sử trước phiên để đối chiếu, không gán tất cả cho W07; commands.json chỉ trong phiên.
- quality.json, light-minutes.csv: kết quả phân tích và phút bị khóa theo nhật ký hiện tại.
- manifest.json: SHA256; backup ZIP local tại artifacts/w07-backup-20261123.zip. Bản đầy đủ chứa metadata vận hành, chưa push công khai.

Không thay đổi W01–W06. Bản sửa thông báo phao chưa được nạp bởi lượt xử lý dữ liệu này. Không gọi API điều khiển, không thay quyền AI.

## Gói công bố Git — 23/11/2026

Git chỉ chứa telemetry chuẩn hóa, nhật ký, metadata phiên, xác nhận người dùng và kết quả chất lượng. Snapshot database đầy đủ/lịch sử lệnh và sự kiện ngoài phiên giữ local, được loại khỏi Git bằng .gitignore; các ZIP sao lưu ở artifacts vẫn giữ nguyên. manifest.json kiểm tra các file công bố; manifest-local.json và ZIP giữ checksum snapshot trước công bố. Chưa đủ metadata để train/test theo pipeline hiện tại.
