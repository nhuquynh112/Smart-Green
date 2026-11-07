# TV1 — chạy pipeline AI trên laptop

Cập nhật 07/11/2026. Không cần ESP32 hoặc Docker cho các lệnh dưới đây.

## Môi trường đã chuẩn bị

Thư mục gốc: `/home/ad/Desktop/Smart-Green`. Môi trường riêng `.venv-ai` đã cài thư viện của dự án. `ai/requirements-tested.txt` ghi phiên bản đã dùng trong lần kiểm thử này (Python 3.12 trên Ubuntu); không phải cam kết chạy trên mọi hệ điều hành.

```bash
cd /home/ad/Desktop/Smart-Green
.venv-ai/bin/python -m pytest -q ai/tests tools/tests
```

Kết quả ngày 07/11: **37 passed** và 8 subtests cho AI/tools; thêm 5 kiểm thử integration đạt. Xem [báo cáo offline mới nhất](AI_OFFLINE_RESULTS_2026-11-07.md). Có kiểm tra chống rò rỉ nhãn qua ranh giới train/validation/test, dữ liệu thiếu, tính nhất quán đặc trưng, baseline/mô hình, bộ kiểm tra dữ liệu đầu vào và pipeline Serial offline.

## 1. Kiểm tra dữ liệu thật trước huấn luyện

```bash
.venv-ai/bin/python -m smart_green_ai.assess firmware/data/prepared/bench_received_session_03.csv --output artifacts/real-readiness-2026-11-06.json
```

Báo cáo lịch sử ngày 06/11 với 13 mẫu thật trả `training_pipeline_ready=false` vì còn thiếu:

- Hai cột `minutes_since_water`, `water_total_ms`: cần lịch sử tưới thực tế đầy đủ.
- `timestamp` của cả 13 mẫu: hiện mới có giờ laptop nhận. Không tự chuyển received_at thành giờ đo.
- `soil_pct` của cả 13 mẫu: chưa hiệu chuẩn bằng đất thật.

Công cụ không sửa dữ liệu gốc và không tự điền các giá trị thiếu. Dataset vượt kiểm tra kỹ thuật cũng không tự được xem là đủ bằng chứng thực nghiệm; vẫn cần đủ các chu kỳ và điều kiện quan sát.

## 2. Chạy mô hình bằng dữ liệu giả lập để kiểm tra phần mềm

```bash
.venv-ai/bin/python -m smart_green_ai.simulate --days 10 --output data/synthetic-tv1-2026-11-06.csv
.venv-ai/bin/python -m smart_green_ai.train data/synthetic-tv1-2026-11-06.csv --horizon 30 --output artifacts/synthetic-tv1-2026-11-06
```

So sánh bốn phương án: giữ độ ẩm hiện tại, ngoại suy độ dốc tuyến tính, Linear Regression và Random Forest. Chọn bằng validation theo thời gian; test dùng để báo cáo. Không trộn ngẫu nhiên. Nhãn vượt ranh giới các tập bị loại.

File kết quả:

- `report.json`: chất lượng dữ liệu, phiên bản, ranh giới tập và MAE.
- `test_predictions.csv`: nhãn và dự đoán của bốn phương án.
- `candidate.joblib`: mô hình/baseline được chọn cùng metadata; chỉ tải file do nhóm tạo và tin cậy.
- `demo_advice.json`: kết quả chạy thử hàm dự đoán sau khi huấn luyện, nếu chạy bước kiểm thử tích hợp.

MAE dùng đơn vị **điểm phần trăm của chỉ số ẩm tương đối**, không phải phần trăm accuracy. Mục `falling_soil_test` tính riêng mẫu có độ ẩm tương lai thấp hơn hiện tại, trong các cửa sổ không tưới đã lọc. Đây là phân nhóm hồi cứu dùng nhãn, không phải điều kiện kích bơm lúc chạy và không đại diện số chu kỳ độc lập.

**Toàn bộ kết quả synthetic chỉ chứng minh chương trình chạy, không dùng làm độ chính xác thực tế của đồ án.** `automatic_irrigation_approved=false` và `can_trigger_pump=false` được giữ nguyên.

## 3. Các việc TV1 tiếp tục khi có phần cứng

1. Đo mốc đất khô/ướt thật, ghi cấu hình và calibration_id; không dùng raw ngoài không khí làm mốc đất khô.
2. Kiểm tra relay OFF lúc boot/reset rồi mới đo bơm và giới hạn tưới. Chưa bật Auto bằng bản bench.
3. Tích hợp timestamp, nhật ký tưới và HTTP với TV2; xác định thời gian bơm thực tế, không dùng quota dự trù làm tổng tưới.
4. Thu liên tục nhiều chu kỳ khô–tưới; tổng hợp theo phút hoàn chỉnh như DATA_AND_AI.md, đánh dấu khoảng thiếu và sự kiện không rõ.
5. Chạy assess, huấn luyện và đánh giá trên dữ liệu thật. AI chỉ đưa đề xuất; ESP32 kiểm tra điều kiện an toàn trước khi tưới.

Backend/PostgreSQL/Web do TV2 phụ trách. Phần pipeline AI này không cần tạo thêm container hay thay schema backend.
