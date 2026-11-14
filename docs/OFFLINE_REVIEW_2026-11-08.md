# Rà soát dữ liệu và AI — 08/11/2026

Phạm vi: đọc builder dữ liệu phút, kiểm tra nhật ký tưới, đặc trưng/train/inference và các test liên quan. Không mở Serial, không đọc/ghi phiên thu đang chạy, không nạp firmware. Đây là rà soát có phạm vi, không phải chứng nhận toàn bộ mã không còn lỗi.

## Lỗi đã sửa

Builder giữ null đúng khi cảm biến đất/không khí invalid nhưng chưa ghi lý do vào excluded_reason; vì vậy quality report có thể báo ít phút bị loại hơn số phút thiếu đầu vào AI.

Đã bổ sung invalid_soil_sensor và invalid_air_sensor vào lý do/thống kê. Giữ nguyên giá trị của cảm biến còn hợp lệ. Một phút lỗi cả hai được tính một lần trong excluded_minutes nhưng có hai lý do; tổng số lý do có thể lớn hơn số phút bị loại. Không nội suy, sửa raw hoặc thay đổi dữ liệu đã thu.

Test hồi quy kiểm tra ba trường hợp: chỉ đất lỗi, chỉ không khí lỗi và cả hai lỗi. Các báo cáo cũ không được tự ghi đè; khi cần, tái tạo từ file phiên đã kết thúc vào output mới.

## Các điều kiện đã đối chiếu trong mã

- Timestamp có múi giờ; giờ lùi trong boot bị từ chối, proxy phải chọn rõ.
- Lịch sử tưới chưa xác nhận hoặc không rõ giữ thiếu; không suy ra tưới tay từ pump_on.
- Model/data kiểm tra calibration, nguồn dữ liệu, phiên bản đặc trưng và time_basis.
- Cửa sổ tương lai không có tưới bổ sung; chia thời gian có purge nhãn ở ranh giới.
- Inference yêu cầu phút hoàn tất, kiểm tra độ mới và chỉ trả đề xuất.

Giới hạn: chưa đánh giá trên dataset thật nhiều chu kỳ, chưa kiểm chứng backend TV2, chưa nghiệm thu phần cứng. Trainer xuất test cùng validation nên phải chốt cấu hình trước đánh giá cuối; xem [kế hoạch AI thật](REAL_AI_EVALUATION_PLAN.md).

Phiếu chuẩn bị buổi thử: [đo lưu lượng bơm](PUMP_FLOW_WORKSHEET.md).

## Kiểm chứng sau sửa

` .venv-ai/bin/python -m pytest -q tools/tests/test_build_ai_dataset.py ai/tests tools/tests/test_prepare_telemetry.py tools/tests/test_calibration.py `: **47 passed, 4 subtests passed**. Các test dùng fixture/tệp tạm, không đọc cổng Serial hoặc phiên thu thật. Đã kiểm tra liên kết tài liệu thay đổi và `git diff --check`.
