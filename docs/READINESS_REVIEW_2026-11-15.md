# Rà soát mức sẵn sàng đồ án — 15/11/2026

Phạm vi: đọc pipeline AI/ánh sáng, API và nhật ký, UI, hồ sơ nghiệm thu; chạy test offline. Không kiểm tra trạng thái live, không mở Serial, không restart backend, không điều khiển bơm. Đây không phải chứng nhận không còn lỗi. Chưa có rubric môn học nên tỷ lệ dưới đây là ước lượng tiến độ, không phải dự báo điểm.

## Mức hoàn thiện

Ước lượng 80–85% phần phát triển và 70–80% mức sẵn sàng bảo vệ. Có telemetry, PostgreSQL, điều khiển với guard, dashboard, nhật ký phiên, dữ liệu W01–W04 và AI có đối chứng. Khoảng trống chính là nghiệm thu bản cuối, tổng hợp báo cáo, đánh giá trên chu kỳ chưa dùng và phục hồi/demo offline. Không quy số mẫu thành chất lượng AI.

## Phát hiện theo ưu tiên

1. **P1 — cấu hình quản trị mặc định** (`backend/app.py:169`): thiếu biến môi trường vẫn có tài khoản/mật khẩu cố định trong source. UI dùng Basic Auth (`backend/static/index.html`, loginForm); nếu phục vụ qua HTTP như các ảnh trước, thông tin xác thực không được mã hóa ở lớp HTTP. Chưa đọc secret hay xác nhận cấu hình live. Trước demo nhiều người: buộc cấu hình riêng, tách chế độ demo; dùng mạng tin cậy/HTTPS khi triển khai. Không tự đổi mật khẩu trong lượt rà soát.
2. **P2 — nhật ký tưới tay chưa cấp dữ liệu cho AI online** (`backend/app.py:251`, `backend/collection_sessions.py:179`): online đọc watering_events, trong khi phiên lưu events ở document. Nhập đầy đủ nhật ký/đánh dấu đối soát không đồng nghĩa online biết thời điểm tưới tay. Cần adapter có đối soát, chống trùng và quy định nguồn chuẩn, hoặc giới hạn rõ AI thật ở offline. Không chỉ bật checkbox để vượt chặn.
3. **P2 — một sự kiện Reboot cũ có thể chặn AI online vô thời hạn** (`backend/ai_service.py:74`): API tải toàn bộ watering_events của thiết bị và hàm trả rỗng khi gặp bất kỳ Reboot. Đây là chặn bảo thủ, không bật bơm sai, nhưng thiếu cách phục hồi sau một chu kỳ đã được đối soát. Cần phạm vi lịch sử tin cậy/điểm đối soát mới và test reset cũ + tưới đã biết; không đơn giản xóa/bỏ qua Reboot.
4. **P2 — demo biểu đồ phụ thuộc Internet** (`backend/static/index.html:11`): Chart.js tải CDN; renderChart trả về khi không có Chart. Cần đóng gói bản thư viện cố định kèm license và thử mất mạng. Font ngoài chỉ ảnh hưởng trình bày.
5. **P2 — chú thích đánh giá AI sai nguồn khi dùng model thật** (`backend/static/index.html:51`): metadata đổi theo bundle nhưng câu bên dưới luôn nói dữ liệu giả lập. Cần lấy cùng data_origin để ghi đúng, thêm test real/synthetic/no model.
6. **P2 — khoảng trống export phục vụ train** (`backend/collection_sessions.py:178–191`): CSV rút gọn thiếu identity/validity/calibration; JSONL đầy đủ vẫn được giữ trong ZIP, không mất raw. Bộ xuất chọn giờ nhận, nên khi mạng trễ có thể gồm mẫu đo trước phiên hoặc thiếu mẫu tới sau khi chốt. Không dùng riêng CSV rút gọn để train; cần quy trình nhập JSONL, đối chiếu giờ đo/nhận, calibration/boot, xử lý flush và chạy quality checks.
7. **P2 — hồ sơ tổng kết lỗi thời**: TV1_REPORT_DRAFT ghi 08/11, TV1_REMAINING_TASKS ghi 12/11; bỏ sót kết quả thật W01–W04/ánh sáng và trạng thái UI hiện tại. Không dùng nguyên bản này để nộp. Các báo cáo theo phiên vẫn có bằng chứng kiểm tra được.
8. **P3 — suy diễn xu hướng ánh sáng từ dao động nhỏ** (`backend/static/index.html:194`): mọi delta khác 0 vẫn gán sáng/tối, chưa có đánh giá nhiễu. Nên chỉ hiển thị biến thiên ADC trước khi có tiêu chí ổn định đã kiểm chứng; không bịa ngưỡng thiếu/thừa sáng cho cây.

## AI và phần cứng

RF60 trên W04 MAE khoảng 6,625, Persistence khoảng 1,005; thêm ánh sáng không giải quyết tổng quát hóa. Bằng chứng phù hợp với lệch phân bố độ ẩm/thiếu chu kỳ train. W05 nên là kiểm tra tiếp theo, giữ cố định mô hình trước khi xem nhãn. Không cần cố ép RF tốt hơn để có báo cáo khoa học đúng.

Checklist phần cứng vẫn là kế hoạch, chưa có biên bản đầy đủ gắn commit cuối. Cần ghi ba phép đo nước riêng, dừng theo thời lượng, STOP/OFF, phao, reset, mất mạng/phục hồi, chống lệnh lặp; quan sát motor và nước riêng vì siphon không được giải quyết bằng code OFF. Không suy từ test native sang phần cứng đã đạt.

## Để hướng tới bài bảo vệ 9,5

1. Chốt rubric và phạm vi TV1/TV2; nếu yêu cầu AI trực tiếp điều khiển thì chế độ quan sát hiện tại chưa đáp ứng phần đó. Không mở quyền điều khiển khi chưa nghiệm thu.
2. Xử lý các mục P1/P2 và nghiệm thu giao diện thật cả mất mạng, phiên start/save/finish/export.
3. Hoàn thành W05 và đánh giá cố định, trình bày baseline, chia phiên/chu kỳ, leakage, bão hòa, MAE và thất bại RF một cách trung thực.
4. Lập biên bản phần cứng bản cuối, sơ đồ dây thật, số đo lưu lượng và video bằng chứng.
5. Hoàn thiện báo cáo tổng hợp, slide, bảng truy vết yêu cầu → test → bằng chứng. Không tuyên bố tiết kiệm nước/AI hiểu nhu cầu cây nếu chưa đo.
6. Chạy demo 5–7 phút và phục hồi database vào môi trường riêng; chuẩn bị video dự phòng và hướng dẫn tái lập. Chưa xác nhận restore đã được thử trong lượt này.

Không có số giờ thu hay số mẫu cố định đảm bảo điểm. Chất lượng giải thích, tính tái lập và bằng chứng nghiệm thu quan trọng hơn bổ sung tính năng mới.

## Kiểm chứng lượt này

- Python AI/tools/backend: **159 passed, 7 skipped, 8 subtests passed**. Các biến thể PostgreSQL cần DB kiểm thử riêng bị bỏ qua; không tính là đạt trong lượt này. Lượt sandbox đầu bị treo khi chạy bộ có HTTP loopback và đã dừng; lượt cấp quyền chạy test local hoàn tất.
- Dashboard: **23 passed**, gồm kiểm tra ID HTML duy nhất sau lỗi khối ánh sáng trùng.
- Firmware native: controller, safety boundaries, runtime, telemetry/control profile và timestamp đều đạt; không nạp board.
- `artifacts/session-w04-2026-11-14/verify_evidence.py`: các manifest W01/W02/W03/W04 và dự đoán/MAE W04 đều đạt.
- Không restart backend, không sửa DB hay firmware. Chưa nghiệm thu browser thật và hardware trong lượt này.
