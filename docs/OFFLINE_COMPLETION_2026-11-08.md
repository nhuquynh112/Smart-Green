# Hoàn thiện offline TV1 — 08/11/2026

Phạm vi: làm việc trên máy tính, không mở Serial, không nạp firmware, không chạy bơm, không sửa main hoặc backend TV2.

## Đã hoàn thiện

| Phần | Kết quả |
| --- | --- |
| Nhật ký tưới | CLI init/add/check; tưới tay và bơm, kiểm tra thời gian, identity và khoảng quan sát |
| Chuẩn hóa AI | CSV phút từ JSONL và nhật ký; giữ thiếu dữ liệu, chặn identity xung đột, loại phút tưới/đổi boot |
| Thời gian | Giờ đo mặc định; giờ nhận proxy chỉ khi chọn rõ, ghi nhãn và kiểm tra model/data khớp nhau |
| AI v2 | water_event_count hỗ trợ tưới tay; model v1 phải huấn luyện lại; chỉ dự đoán phút hoàn tất |
| Demo offline | Một lệnh chạy toàn luồng trên dữ liệu synthetic, xuất HTML, MAE, biểu đồ và đề xuất mẫu |
| Bàn giao TV2 | Schema CSV, tích hợp predict, quy tắc ACK/dedup và ma trận thử backend thật |
| Nghiệm thu | Checklist từng giai đoạn: chưa cấp nguồn tải bơm → bình đong → cây/AI quan sát |
| Báo cáo | Bản nháp TV1, phân biệt kết quả thật cơ bản với mô phỏng và phần chưa nghiệm thu |

## Demo v2 đã chạy

- 10 ngày synthetic, 14400 telemetry hợp lệ.
- 3 tập theo thời gian; train 8334, validation 2758, test 2789 cửa sổ.
- Nhật ký có 9 sự kiện tưới mô phỏng; không giả thời gian bơm cho sự kiện tưới tay.
- Dataset SHA256: `4d38b8bfd9c77606eac1abcbc0318dc20678ee9e17d6cf9870af8e018589b877`.
- Feature version: `v2-watering-events`.
- Chọn theo validation: `linear_regression`.
- `can_trigger_pump=false` và `automatic_irrigation_approved=false`.

| Phương án | Validation MAE | Test MAE |
| --- | ---: | ---: |
| persistence | 0.7388 | 0.7423 |
| linear_extrapolation | 0.0590 | 0.0630 |
| linear_regression | 0.0382 | 0.0365 |
| random_forest | 0.1027 | 0.1570 |

MAE tính bằng điểm phần trăm chỉ số độ ẩm tương đối. **Toàn bộ bảng này là dữ liệu giả lập, không phải độ chính xác trên cây thật.** Các cửa sổ tương quan và việc qua kiểm thử không chứng minh đủ bằng chứng khoa học.

## Chạy lại không cần thiết bị

Tại thư mục gốc:

```bash
source .venv-ai/bin/activate
python -m pip install -e '.[test,report]'
python tools/demo_offline.py --days 10 --output artifacts/offline-demo-v2-new
```

Nếu chưa có môi trường, dùng `python3 -m venv .venv` rồi kích hoạt `.venv/bin/activate`. Thư mục output phải mới. Báo cáo nằm trong `report/index.html` của thư mục output.

Kết quả đã tạo trên máy này: `artifacts/offline-v2-2026-11-08/report/index.html`. Dataset/model/report sinh tự động được gitignore; mã nguồn và tài liệu kết quả được commit để tái tạo.

## Tài liệu dùng tiếp

- [Nhật ký tưới và tạo dữ liệu](WATERING_AND_AI_DATASET.md)
- [Tích hợp AI cho TV2](handoff/AI_INTEGRATION.md)
- [Kịch bản nghiệm thu khi có phần cứng](TV1_HARDWARE_ACCEPTANCE.md)
- [Bản nháp báo cáo TV1](TV1_REPORT_DRAFT.md)

## Việc còn chờ

1. TV2 triển khai/chốt backend thật, chạy các ca lưu bền, xác thực, ACK và lệnh trùng.
2. Xác minh mức kích relay trước khi chuyển từ bringup sang runtime: hai bản hiện có mặc định khác nhau.
3. Đo lưu lượng, thời gian ngắt, reset và bảo vệ cơ khí/điện; chưa bật tưới tự động lên cây.
4. Thu dữ liệu thật có thời gian và nhật ký, qua nhiều chu kỳ; đánh giá AI thật sau khi đủ dữ liệu.
5. Nghiệm thu tích hợp thực tế, ghi video và hoàn thiện các bảng kết quả còn thiếu trong báo cáo.

Không còn cần thiết bị để đọc tài liệu, chạy demo hoặc kiểm thử phần mềm. Các mục thực nghiệm phía trên không thể được thay bằng kết quả mô phỏng.

## Kết quả kiểm thử cuối

- `python -m pytest -q ai/tests tools/tests integration`: **59 passed**, 8 subtests passed.
- `bash tools/test_firmware.sh`: controller và runtime đều đạt.
- Đã chạy demo 10 ngày, kiểm tra metadata, đề xuất mẫu, biểu đồ MAE và biểu đồ dự đoán.
- Đã kiểm tra các liên kết Markdown nội bộ và `git diff --check`.
- Các kiểm thử không mở cổng Serial, không xác nhận FreeRTOS/GPIO/NVS hay PostgreSQL thật.
