# W05 — gói nghiên cứu đã chọn lọc

Phiên 15/11/2026, 12:16:37–20:00:07 UTC+7. 927 mẫu, cùng chu kỳ tưới W04. Nhật ký được người dùng xác nhận ngày 16/11; lần tưới trước kết thúc khoảng 12:21 ngày 14/11. Không dùng W05 để train/chọn lại mô hình trong đánh giá này.

- telemetry.jsonl: giá trị đo gốc theo danh sách trường cho phép; không phải toàn bộ payload/DB. Giữ identity kỹ thuật để kiểm tra trùng/reset, timestamp, calibration, validity, trạng thái phao/bơm.
- journal.json: nhật ký đã đối soát, bỏ một shade_end trùng; provenance.json giữ ghi chú mốc bị bỏ và checksum ZIP nguồn.
- light-minutes.csv: dataset phút đã xử lý, gồm đặc trưng đầu vào cho evaluator; không thay mẫu thiếu bằng số giả.
- predictions-30/60.csv và evaluation.json: kết quả mô hình đóng băng, 418/388 cửa sổ chung. Các đường dẫn input trong evaluation.json ghi lại lần chạy gốc ở artifacts; có thể tái lập bằng lệnh dưới đây.
- quality.json, overview.png: chất lượng sau xác nhận và biểu đồ.
- manifest.json: checksum các file gói này.

Không chứa bản xuất database đầy đủ, ZIP gốc, cấu hình đăng nhập, API key hay thông tin mạng. Dữ liệu vẫn có thời gian và mã thiết bị thực nghiệm; không phải dữ liệu đã ẩn danh hoàn toàn. Bản gốc đầy đủ giữ cục bộ tại artifacts/session-w05-2026-11-15; không xóa bản gốc.

Từ gốc repository, kiểm tra checksum, tái dựng phút và MAE:

```bash
PYTHONPATH=ai:tools .venv-ai/bin/python datasets/w05/verify.py
```

Chạy lại các mô hình cố định đã có trong repository vào thư mục mới:

```bash
PYTHONPATH=ai .venv-ai/bin/python -m smart_green_ai.evaluate_light_holdout \
  --data datasets/w05/light-minutes.csv \
  --models artifacts/light-experiment-20261115 \
  --output artifacts/w05-research-rerun
```

Không điều khiển bơm. RF có ánh sáng vẫn thua Persistence; xem docs/W05_REVIEW_2026-11-15.md. Gói này dùng cho đối chiếu đồ án, chưa đại diện nhiều cây/chậu hay nhiều chu kỳ độc lập.
