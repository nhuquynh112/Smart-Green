# Báo cáo kỹ thuật TV1 — bản nháp có phân biệt bằng chứng

Cập nhật 08/11/2026. Phạm vi: một chậu cây, cảm biến, ESP32, điều khiển tại thiết bị, dữ liệu đầu vào và dự báo AI. FastAPI/PostgreSQL/dashboard do TV2 phụ trách; hai bên cùng nghiệm thu tích hợp.

## 1. Mục tiêu và phạm vi

Smart-Green theo dõi môi trường trồng cây và hướng tới tưới có kiểm soát. TV1 phát triển hai lớp: điều khiển dựa trên quy tắc an toàn tại ESP32 và dự đoán độ ẩm để cung cấp thông tin cho hệ thống. Dự đoán không trực tiếp điều khiển GPIO hoặc bỏ qua phao, hạn mức và điều kiện cảm biến.

Cây thử nghiệm là cẩm nhung trong chậu có lỗ thoát nước. Kết quả ban đầu mới chứng minh đọc cảm biến, hiệu chuẩn và bơm có giám sát; chưa chứng minh hệ thống tự chăm sóc cây hoặc tiết kiệm nước.

## 2. Thiết kế thiết bị và dữ liệu

ESP32 đọc cảm biến đất tại GPIO34, ánh sáng GPIO35, DHT22 GPIO27, phao GPIO26 và điều khiển relay GPIO25. ESP32 nhận nguồn USB; bơm/relay dùng adapter 5V–2A theo bố trí đã thử. Bơm nối qua COM–NO. Cần bổ sung sơ đồ điện đúng phần cứng thực tế, mức kích relay và ảnh bố trí sau khi nghiệm thu.

Độ ẩm đất dùng hai mốc `dry_raw=2511`, `wet_raw=979` từ lần hiệu chuẩn đã ghi nhận. Công thức nội suy giới hạn 0–100% biểu diễn chỉ số tương đối, không phải hàm lượng nước thể tích. Ánh sáng mới có ADC raw, chưa đo lux. Sau tưới, chỉ số trong chậu từng ở khoảng 84–85%; đây không phải ngưỡng khuyến nghị tưới.

Mỗi telemetry có device_id, boot_id và sample_seq để nhận diện duy nhất. Raw được giữ nguyên; giờ đo, giờ nhận và giờ nhập database có ý nghĩa khác nhau. Log lỗi được ghi nhận, không tự sửa nội dung thành số đo hợp lệ.

## 3. Firmware và an toàn

Bản bringup dành cho kiểm tra có giám sát: đọc JSON Serial, dry/wet, arm/pump/stop và giới hạn xung. Cờ thử bơm hiện khóa. Bản runtime có cảm biến, task mạng, lệnh/ACK, nhật ký NVS và logic OFF/MANUAL/AUTO; còn chờ nghiệm thu trên mạch thật.

Auto-Rule có ngưỡng thấp/cao, yêu cầu mẫu khô liên tiếp, khoảng nghỉ, giới hạn xung và quota. Khi đủ điều kiện, phao cạn và các lỗi guard phải ngăn/ngắt output. AUTO khi mất mạng và boot chưa có đồng hồ là hai trạng thái khác nhau: chưa có giờ hợp lệ thì khóa bật bơm.

Giới hạn cần công bố: quota hiện là cửa sổ cố định, queue telemetry hữu hạn có thể mất mẫu, nhật ký sự kiện hữu hạn, guard là phần mềm. GPIO ON không chứng minh đã có nước chảy. Thể tích nước phải được đo riêng; không tự suy ra từ actual_ms khi chưa hiệu chuẩn lưu lượng.

## 4. Xử lý dữ liệu và nhật ký tưới

Parser kiểm tra JSON, kiểu dữ liệu, dải ADC/phần trăm, trạng thái hợp lệ và timestamp có múi giờ. Bản trùng được loại theo identity, bản xung đột được báo lỗi. Log cũ thiếu thời gian không được gán giờ hiện tại hoặc đoán từ tên file.

Pipeline v2 bổ sung nhật ký tưới tay/bơm: thời điểm bắt đầu/kết thúc, lượng nước nếu biết, thời gian bơm nếu đo được, khoảng quan sát và khoảng không rõ. Người quan sát xác nhận tính đầy đủ sau phiên; phần mềm không thể tự chứng minh nhật ký là đầy đủ.

CSV phút dùng median theo phút UTC đã hoàn tất. Phút thiếu dữ liệu, tưới, đổi boot hoặc có lịch sử không rõ bị loại khỏi cửa sổ dự báo. `water_event_count` đếm cả tưới tay và bơm; không tạo ms giả cho tưới tay. Khi chỉ có giờ nhận, lựa chọn `received_at_proxy` phải hiện rõ và đánh giá sai số thời gian riêng.

## 5. Phương pháp AI

Bài toán chính: dự đoán chỉ số ẩm tương đối sau 30 phút với điều kiện không tưới thêm. Đặc trưng gồm độ ẩm hiện tại, lag 5/15 phút, độ dốc 15 phút, nhiệt độ, độ ẩm không khí, thời gian từ lần tưới và chu kỳ giờ UTC sin/cos.

So sánh bốn phương án: giữ giá trị gần nhất, ngoại suy xu hướng tuyến tính, Linear Regression và Random Forest. Chia theo thời gian 60/20/20; loại nhãn huấn luyện/validation chạm ranh giới tập sau. Chọn theo validation, test dành để báo cáo. MAE tính bằng điểm phần trăm độ ẩm tương đối, không gọi là phần trăm accuracy.

Chỉ đánh giá các cửa sổ có lịch sử/tương lai hoàn chỉnh và không tưới bổ sung. Vì vậy MAE không mô tả mọi trạng thái hoạt động hoặc hiệu quả điều khiển. Các mẫu gần nhau tương quan; đủ số hàng không đồng nghĩa đủ chu kỳ khô–tưới độc lập. Không chỉnh mô hình lặp lại dựa trên test cuối.

Feature version v2 thay bộ đếm thời gian bơm bằng bộ đếm sự kiện; model v1 phải huấn luyện lại. Hàm inference kiểm tra version, calibration, nguồn và cơ sở thời gian. Đầu ra luôn `can_trigger_pump=false` trong giai đoạn này.

## 6. Kết quả đã có

| Hạng mục | Bằng chứng hiện tại | Phạm vi kết luận |
| --- | --- | --- |
| Cảm biến, relay, bơm | Bàn giao phần cứng ngày 07/11 | Đã hoạt động trong thử nghiệm cơ bản có giám sát |
| Hiệu chuẩn đất | Hai mốc raw và soil_valid | Ánh xạ tương đối của lần thử hiện tại |
| Parser | 42 log: 586 bản ghi hợp cấu trúc, 133 soil_valid | Log bench còn thiếu thời gian, chưa đủ để train thật |
| Firmware core/runtime | Kiểm thử native C++ và HTTP mô phỏng | Xác minh logic; chưa xác minh GPIO/FreeRTOS/NVS thật |
| AI v1 offline | Báo cáo ngày 07/11, dữ liệu synthetic | Pipeline chạy; không phải MAE thực nghiệm |
| AI v2 offline | Báo cáo và demo ngày 08/11 | Kiểm thử toàn luồng nhật ký → CSV → model → đề xuất |

Xem [kết quả offline v2](OFFLINE_COMPLETION_2026-11-08.md) để lấy số liệu và lệnh tái tạo mới nhất. Không trộn số liệu synthetic vào bảng kết quả trên cây thật.

## 7. Nội dung phải bổ sung sau nghiệm thu

- Sơ đồ/ảnh mạch thật; mức OFF lúc boot/reset và cách chống nước.
- Bảng đo lưu lượng, độ phân tán, thời gian ngắt thực tế và lựa chọn hạn mức.
- Dataset nhiều chu kỳ, phạm vi điều kiện, khoảng mất mẫu, nhật ký tưới và thay đổi vị trí cảm biến.
- Kết quả các ca trong checklist phần cứng, bằng chứng backend lưu bền và chống lặp lệnh.
- MAE thật của baseline và model, biểu đồ dự báo, sai số gần ngưỡng và phân tích lỗi.
- Video demo, giới hạn, tình huống chưa đạt và hướng dẫn tái tạo.

Các mục này chưa có số liệu thì để “chưa nghiệm thu”, không điền giá trị minh họa làm kết quả.

## 8. Tài liệu triển khai

- [Quy trình dữ liệu AI v2](WATERING_AND_AI_DATASET.md)
- [Hợp đồng API](TV2_CONTRACT.md)
- [Bàn giao AI cho TV2](handoff/AI_INTEGRATION.md)
- [Kịch bản nghiệm thu phần cứng](TV1_HARDWARE_ACCEPTANCE.md)
- [Thiết kế dữ liệu và AI](DATA_AND_AI.md)
