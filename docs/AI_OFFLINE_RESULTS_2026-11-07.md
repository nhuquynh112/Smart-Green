# Kết quả kiểm thử AI offline — 07/11/2026

**DỮ LIỆU GIẢ LẬP — chỉ kiểm tra pipeline phần mềm, không phải kết quả trên cây thật.**

## Thiết lập

- 10 ngày mô phỏng, 14400 mẫu theo phút; dự đoán trước 30 phút nếu không tưới thêm.
- 13950 cửa sổ đủ điều kiện; sau loại nhãn vượt ranh giới chia tập: train 8340, validation 2760, test 2790.
- Chia theo thời gian, chọn mô hình bằng validation; test dùng để báo cáo.
- Dataset SHA256: `cf1d440cb824369ff0d788b0cbe128196029381df20d25803d3a728af797fdac`.
- Thời gian trong dataset bắt đầu tháng 01/2026 là thời gian mô phỏng, không phải ngày thu trên cây thật.

## MAE (điểm phần trăm độ ẩm tương đối)

| Phương án | Validation | Test |
| --- | ---: | ---: |
| persistence | 0.7388 | 0.7424 |
| linear_extrapolation | 0.0590 | 0.0630 |
| linear_regression | 0.0382 | 0.0365 |
| random_forest | 0.1026 | 0.1564 |

Linear Regression được chọn theo validation. MAE thấp hơn chỉ thể hiện hiệu quả trên bộ giả lập này; chưa thể suy ra độ chính xác trên cây thật hoặc lượng nước tiết kiệm. Các cửa sổ gần nhau tương quan, không phải thử nghiệm độc lập.

`automatic_irrigation_approved=false`; hàm dự đoán chỉ trả đề xuất với `can_trigger_pump=false`.

## Chạy lại từ thư mục gốc

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,report,capture]'
python -m smart_green_ai.simulate --days 10 --output data/synthetic-tv1-2026-11-07.csv
python -m smart_green_ai.train data/synthetic-tv1-2026-11-07.csv --horizon 30 --output artifacts/synthetic-tv1-2026-11-07
python tools/export_ai_report.py artifacts/synthetic-tv1-2026-11-07 --output artifacts/ai-report-synthetic-2026-11-07
```

Báo cáo HTML tự chứa: `artifacts/ai-report-synthetic-2026-11-07/index.html`. Cùng thư mục có biểu đồ PNG/SVG, `metrics.csv` và `provenance.json`. Dataset, model joblib và báo cáo sinh tự động được gitignore; tài liệu này giữ kết quả tóm tắt để bàn giao. Phiên bản thư viện thực tế được ghi trong `report.json`; khác phiên bản có thể làm thay đổi kết quả số.

## Xác minh phần mềm

- `python -m pytest -q ai/tests tools/tests integration`: **42 passed**, 8 subtests passed.
- `bash tools/test_firmware.sh`: controller và runtime đều đạt.
- Biểu đồ MAE và dự đoán đã được kiểm tra trực quan.
- Chưa nghiệm thu ESP32/runtime với backend thật, chưa nhập PostgreSQL và chưa đánh giá AI trên dữ liệu thật đủ điều kiện.
