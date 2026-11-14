# TV1 — Đối chiếu yêu cầu và kiểm thử

Rà soát 08/11/2026, phục vụ ngày 4–5 và 10–12. Chỉ các test host C++ được chạy lại trong lượt này; các test Python dưới đây được đối chiếu mã và báo cáo offline trước đó. Không mở Serial, không nạp firmware, không đọc/ghi file phiên thu đang chạy.

## Ma trận bằng chứng

Đường dẫn mã tính từ thư mục gốc repository.

| Yêu cầu | Test hiện có | Bằng chứng thật còn cần |
| --- | --- | --- |
| Khóa khi chưa commissioning | `firmware/test/native/test_controller.cpp`, `test_profile.cpp` | A01: đo GPIO OFF lúc boot/reset |
| Ba mẫu khô liên tiếp, dừng ở ngưỡng cao | `test_controller.cpp`; `test_safety_boundaries.cpp::noisy_dry_samples` | C02: cảm biến thật quanh ngưỡng |
| Thời gian nghỉ, biên đúng cooldown | `test_safety_boundaries.cpp::cooldown_boundary` | B03: không có nước thêm trong khoảng nghỉ |
| Giới hạn xung, sensor stale, phao cạn | `test_controller.cpp`, `test_runtime.cpp` | B02/B06/B07: đo độ trễ ngắt thật |
| Hạn mức số lần và thời gian, giữ qua reset | `test_controller.cpp`; `test_safety_boundaries.cpp::time_quota_and_reboot` | B04/B05: NVS thật, kiểm tra sát biên cửa sổ 24 giờ |
| Hàng đợi đầy chặn tưới, chỉ ACK đầu hàng | `test_safety_boundaries.cpp::full_event_queue` | B08: lưu và gửi sự kiện thật |
| AI chỉ chạy đúng mode và ngưỡng cho phép | `test_safety_boundaries.cpp::ai_mode_and_ceiling` | Lệnh từ server và output thật; hiện AI bị khóa |
| Không bật khi giờ lùi hoặc chưa có giờ | `test_safety_boundaries.cpp::clock_rollback`, `test_runtime.cpp` | A03: NTP/boot/mất mạng thật |
| Sai thiết bị/key, hết hạn, mất ACK, chống lặp | `integration/test_http_runtime.py` | A06/A07: API TV2, PostgreSQL và reset ESP32 |
| AUTO độc lập mạng, phao vẫn có hiệu lực | `test_runtime.cpp`, `integration/test_http_runtime.py::test_auto_without_server_respects_empty_tank` | C03: mất mạng thật; OFF/MANUAL không tự chuyển AUTO |
| OFF trước lưu trạng thái khi storage lỗi | `test_runtime.cpp` | Độ trễ GPIO và hành vi flash/task thật |
| Không bịa thời gian/nhật ký tưới | `tools/tests/test_prepare_telemetry.py`, `test_build_ai_dataset.py` | Nhật ký người quan sát và kiểm tra phiên thật |
| Không rò rỉ nhãn tương lai, cùng đặc trưng train/predict | `ai/tests/test_pipeline.py` | Đánh giá dataset thật, tập test độc lập theo thời gian |

ID A/B/C tham chiếu [checklist phần cứng](TV1_HARDWARE_ACCEPTANCE.md). Test mô phỏng không xác nhận các ID đó đạt.

## Bổ sung và kết quả lượt rà soát

Đã thêm `firmware/test/native/test_safety_boundaries.cpp` với sáu nhóm: cooldown; quota thời gian qua reset; queue đầy; AI mode/ngưỡng; chuỗi mẫu khô bị nhiễu; đồng hồ lùi. Runner `tools/test_firmware.sh` tự chạy file mới.

`bash tools/test_firmware.sh` đạt: controller, sáu nhóm biên an toàn, runtime, profile telemetry/control và timestamp. Executable chỉ được tạo trong thư mục tạm; không gọi PlatformIO upload hoặc thiết bị USB.

Không sửa logic vận hành. Kết quả này không phải chứng nhận an toàn phần cứng.

## Khoảng trống còn giữ lại

- Quota là cửa sổ cố định, không bảo đảm hạn mức trên mọi cửa sổ trượt 24 giờ.
- Test HTTP dùng core và server giả; không chứng minh lịch FreeRTOS, guard task, flash NVS hoặc backend TV2.
- Chưa có phép đo relay dính, siphon/chảy tiếp sau OFF, thời gian ngắt hoặc lưu lượng thật.
- Chưa có bằng chứng toàn luồng AI → API → ESP32 → nước thực tế. AI chỉ đề xuất là mức dự phòng, không phải hoàn thành mục tiêu điều khiển AI của kế hoạch gốc.
