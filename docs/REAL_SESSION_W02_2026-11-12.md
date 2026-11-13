# W02 — đánh giá candidate W01 cố định

Ngày xử lý: 13/11/2026. Nguồn: PostgreSQL local, transaction REPEATABLE READ READ ONLY.
Không ghi database, không bật bơm, không train lại hoặc thay candidate W01.

## Phạm vi và nhật ký

W02: ngày 12/11/2026, 14:55 ≤ received_at < 22:55, giờ Việt Nam (UTC+07),
thiết bị garden-01, data_origin=real, calibration soil-2511-979.
Người dùng xác nhận không tưới thêm/di chuyển cảm biến; lần tưới gần nhất là W01,
11/11 khoảng 12:13–12:14, khoảng 4 muỗng cà phê. Dùng 12:14 làm mốc kết thúc
với độ chính xác đến phút như nhật ký W01, không quy đổi thành ml.

**W02 là phiên ghi về sau của cùng chu kỳ tưới W01, không phải chu kỳ tưới độc lập.**
Không suy ra nhu cầu nước vật lý từ chỉ số soil_pct tương đối.

## Chất lượng dữ liệu

- Snapshot 952 bản ghi; parser chấp nhận 952, không trùng/xung đột/nhảy sequence trong từng boot.
- Hai boot: bbaf7f8eb54d21c0 (210 mẫu), 6aff9bb772b2feef (742 mẫu).
- 2 mẫu chưa có timestamp, clock_ready=false, bỏ khỏi tổng hợp giờ đo; không thay bằng received_at.
- 950 mẫu có giờ đo; 479 mốc phút từ 14:56 đến 22:54. Không có mốc 14:55 do chưa có giờ đo.
- 3 phút thiếu 16:41–16:43; phút 16:44 loại do boot_boundary. Còn 475 phút đủ dữ liệu.
- Có khởi động lại trong khoảng 16:40–16:44; chưa xác định nguyên nhân. Không nội suy hoặc nối qua khoảng này.
- 952 mẫu soil_valid/air_valid=true; mode OFF, pump_on=false; không có event bơm trong phạm vi xuất.
- Soil phút: 0,163–6,625%, trung vị 5,679%; nhiệt độ 30,4–32,55°C; độ ẩm khí 64,6–71,1%.
- Soil tăng trong phần lớn phiên dù không tưới thêm theo nhật ký. Giữ nguyên quan sát, không sửa cho thành đường giảm hoặc tự gán nguyên nhân.

`assess.quality.missing_minutes=0` chỉ có nghĩa CSV đã chứa đủ hàng trên lưới.
Ba hàng missing_telemetry vẫn có identity và giá trị cảm biến null; nguồn xác định thiếu
là minute-data.quality.json/excluded_reason, không dùng con số 0 để kết luận truyền đủ.
Cảnh báo chung về hiệu chuẩn/nhật ký trong assess phát sinh từ hàng loại, không chứng minh
calibration hoặc nhật ký sai.

## Phương pháp đánh giá

Giữ feature v2-watering-events và 9 feature như W01; 16 phút lịch sử hợp lệ,
không tưới trong lịch sử và tương lai dự báo. Không có fitting hay chọn mô hình trên W02.
Dùng toàn bộ cửa sổ hợp lệ W02 để đánh giá candidate đã chọn bằng validation W01.
30 phút: 385 cửa sổ (92 giảm ẩm). 60 phút: 325 cửa sổ (50 giảm ẩm).
Các cửa sổ tương quan theo thời gian, không phải các thử nghiệm độc lập.

Candidate được lưu chỉ chứa phương án thắng validation W01: Persistence (30),
Random Forest (60). Hai baseline tính trực tiếp. Không có estimator LR hoặc RF30
đã fit trong bundle nên không công bố điểm W02 của các mô hình đó hoặc refit để giả là cùng artifact.

MAE: điểm phần trăm chỉ số đất đã hiệu chuẩn; số nhỏ hơn tốt hơn.

| Horizon | Phương án | MAE W02 | MAE nhóm giảm ẩm | Candidate W01 |
|---|---|---:|---:|---|
| 30 | persistence | 0.301872 | 0.183051 | Có |
| 30 | linear_extrapolation | 0.568903 | 0.675446 |  |
| 60 | persistence | 0.464852 | 0.122715 |  |
| 60 | linear_extrapolation | 1.097108 | 1.224543 |  |
| 60 | random_forest | 1.852342 | 2.054644 | Có |

Random Forest 60 phút sai số lớn hơn Persistence khoảng 4 lần trên W02. Không chọn lại
candidate từ test. Trong 325 cửa sổ 60 phút, minutes_since_water đều vượt miền fit W01
(W01: 17–227 phút, W02: 1618–2021 phút); 236 cửa sổ có soil hiện tại ngoài miền fit.
Đây là kiểm tra thay đổi miền dữ liệu, không chứng minh quan hệ nhân quả với sai số.

Readiness chạy lại: horizon30 có thể chia train/validation/test 201/47/77;
horizon60 bị chặn nếu train riêng W02 vì quá ít validation sau purge. Đây là kiểm tra
khả năng huấn luyện mới, không cản đánh giá candidate cố định trên 325 cửa sổ.
Không train lại, không nới điều kiện chia tập. `automatic_irrigation_approved=false`.

## Tái lập và bằng chứng

Snapshot và scripts nằm trong `artifacts/session-w02-2026-11-12/`.
Script export đọc cấu hình kết nối local, không chứa mật khẩu. Chỉ chạy lại vào nơi mới,
không ghi đè snapshot; script export và evaluator từ chối tệp/thư mục đích đã tồn tại.
Các lệnh đã chạy từ repo root:

```bash
.venv-ai/bin/python artifacts/session-w02-2026-11-12/export_snapshot.py
.venv-ai/bin/python tools/prepare_telemetry.py artifacts/session-w02-2026-11-12/telemetry.jsonl --output-dir artifacts/session-w02-2026-11-12/prepared
.venv-ai/bin/python tools/build_ai_dataset.py artifacts/session-w02-2026-11-12/telemetry.jsonl --journal artifacts/session-w02-2026-11-12/watering-journal.json --output artifacts/session-w02-2026-11-12/minute-data.csv --as-of 2026-11-12T22:55:00+07:00
.venv-ai/bin/python artifacts/session-w02-2026-11-12/evaluate_frozen.py
PYTHONPATH=ai .venv-ai/bin/python -m smart_green_ai.assess artifacts/session-w02-2026-11-12/minute-data.csv --horizon 30 --output artifacts/session-w02-2026-11-12/readiness-30.json
PYTHONPATH=ai .venv-ai/bin/python -m smart_green_ai.assess artifacts/session-w02-2026-11-12/minute-data.csv --horizon 60 --output artifacts/session-w02-2026-11-12/readiness-60.json
```

Đã kiểm tra identity/time_basis/feature version/horizon của bundle khớp dataset;
tất cả thời điểm feature W02 sau nhãn cuối test W01; tính lại MAE từ CSV xuất ra khớp JSON.
Hash candidate trước/sau đánh giá không đổi. File nguồn không bị chỉnh sửa.
Hai report JSON nhỏ và nhật ký lưu tại docs/w02-evidence; checksum dữ liệu và model
trong report/manifest. Theo yêu cầu người dùng ngày 13/11, thư mục snapshot W02 (gồm 19 tệp dữ liệu, script và ảnh)
được thêm đích danh vào Git dù artifacts/ mặc định bị ignore. Không thêm cấu hình kết nối
hoặc dữ liệu các phiên khác. Bản ZIP local là bản sao trùng nội dung, không cần lưu thêm vào Git.

## Việc tiếp theo

1. W03 ghi chu kỳ tưới mới khi phù hợp nhu cầu cây, cố định cảm biến/ống và ghi nhật ký.
2. Giữ W01 candidate và công bố kết quả baseline dù ML chưa tốt hơn; không bật tưới bằng AI.
3. Nếu dùng W02 để điều chỉnh/huấn luyện mô hình mới, W02 trở thành dữ liệu phát triển,
   cần một phiên tương lai chưa dùng để đánh giá cuối.
4. Tìm nguyên nhân reboot khi không thu; không đoán là người dùng reset hoặc mất điện.
