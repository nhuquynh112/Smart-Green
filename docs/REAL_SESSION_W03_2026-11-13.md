# W03 — Thu dữ liệu và đánh giá độc lập theo thời gian

Ngày 13/11/2026, giờ Việt Nam (UTC+07). Xử lý offline; không thay đổi database, firmware, dịch vụ hoặc điều khiển bơm.

## Nhật ký và phạm vi

Người dùng xác nhận phiên **10:00–18:00**, không thay đổi hoặc tưới thêm. Lần tưới gần nhất theo nhật ký là W01 ngày 11/11 lúc 12:13–12:14, khoảng 4 muỗng cà phê, chưa đo thể tích bằng mL. W01, W02 và W03 là ba phiên ghi của cùng một chu kỳ tưới, không phải ba chu kỳ tưới độc lập.

Snapshot ban đầu có **1.066 bản ghi**, tới 18:54:44. Phân tích W03 chỉ dùng **956 bản ghi nhận trong [10:00,18:00)**; **110 bản ghi sau 18:00 không được đưa vào đánh giá**, vẫn giữ nguyên trong snapshot. Giờ kết thúc phiên do người dùng xác nhận không được diễn giải thành giờ rút USB.

## Chất lượng dữ liệu

- Mẫu nhận đầu tiên 10:02:14; mẫu cuối 17:59:43. Không có dữ liệu chứng minh khoảng 10:00–10:02.
- 956 mẫu được chấp nhận, không trùng, không phát hiện lỗi thứ tự sequence hoặc thời gian qua công cụ chuẩn bị dữ liệu.
- Một mẫu đầu chưa có thời gian thiết bị/đồng hồ chưa sẵn sàng: giữ trong dữ liệu gốc, loại khỏi bước tạo dữ liệu theo phút.
- 955 mẫu có thời gian đo tạo **478 phút hợp lệ**, từ 10:02 đến 17:59. Nhịp đo trung vị 30 giây (29–31 giây); không có phút thiếu trong khoảng ghi này.
- Một boot_id; tất cả mẫu ở OFF, pump_on=false; không có sự kiện bơm trong snapshot. Dữ liệu không cho thấy reset trong phần phiên quan sát được.
- soil_valid và air_valid đều true trên 956 mẫu. Đây là cờ hợp lệ từ firmware, không chứng minh độ chính xác vật lý.
- tank_ok=false ở 449 mẫu, true ở 507 mẫu. Cần kiểm tra phao riêng trước thử điều khiển; không suy diễn bình thực sự hết nước từ cờ này. Cờ phao không thuộc bộ đặc trưng dự báo hiện tại.
- Chưa có light_lux; ánh sáng vẫn là ADC thô. Chỉ số soil_pct theo hiệu chuẩn cảm biến, không phải độ ẩm thể tích đất đã được kiểm chứng.

## Đánh giá mô hình W01 giữ nguyên

Không fit lại, chọn lại hay triển khai mô hình bằng W03. Đánh giá toàn bộ cửa sổ đủ lịch sử 15 phút và đủ tương lai không tưới; không nội suy dữ liệu thiếu. Nhãn là chỉ số cảm biến tương lai, không phải nhãn “cây cần tưới”. MAE tính bằng **điểm phần trăm chỉ số độ ẩm**. MAE giảm ẩm dùng các cửa sổ có target thấp hơn giá trị hiện tại (197 cửa sổ ở 30 phút, 200 ở 60 phút).

| Chân trời | Phương pháp | Cửa sổ | MAE | MAE giảm ẩm |
|---|---|---:|---:|---:|
| 30 phút | persistence | 433 | 0.3286 | 0.2947 |
| 30 phút | linear_extrapolation | 433 | 0.6915 | 0.7066 |
| 60 phút | persistence | 403 | 0.4544 | 0.3481 |
| 60 phút | linear_extrapolation | 403 | 1.2573 | 1.3412 |
| 60 phút | random_forest | 403 | 0.9557 | 0.7125 |

Candidate W01 ở 30 phút là persistence; ở 60 phút là Random Forest. Các mô hình ML không được lưu từ W01 không được huấn luyện lại để báo điểm W03.

**Persistence tốt hơn Random Forest ở 60 phút** (0,4544 so với 0,9557). Kết quả này không đủ cơ sở để cho AI tự bật bơm. Thời gian kể từ lần tưới của tất cả 403 cửa sổ 60 phút nằm ngoài miền huấn luyện W01; độ ẩm không khí của 367 cửa sổ cũng vượt miền fit. Đây là dấu hiệu khác biệt đầu vào, không phải bằng chứng riêng lẻ xác định nguyên nhân sai số.

Kiểm tra readiness kỹ thuật cho cả 30 và 60 phút đạt điều kiện tạo cửa sổ/chia tập có purge. Tuy nhiên **real_world_evidence_sufficient=false** và **automatic_irrigation_approved=false**. Không dùng các tập chia readiness để huấn luyện trong lần xử lý này. Cờ ai_ready=false ở bản xuất thô là kiểm tra xuất bench trước khi bổ sung nhật ký, không phủ định kết quả readiness của dữ liệu theo phút đã xử lý.

## Giới hạn và việc tiếp theo

W03 xác nhận pipeline hoạt động trên một phiên muộn hơn, nhưng các cửa sổ chồng lấn không phải các quan sát độc lập. Chưa chứng minh khả năng tổng quát qua nhiều cây/chậu hoặc chu kỳ tưới. Giữ W01 làm mốc so sánh; nếu dùng W02/W03 để cải tiến mô hình thì cần một phiên tương lai chưa dùng để đánh giá cuối cùng. Phiên tiếp theo nên ghi đủ trước/sau một lần tưới khi cây thực sự cần, cố định vị trí cảm biến và ghi thời gian/lượng nước; không tưới hoặc làm khô cây chỉ để tạo dữ liệu.

## Tệp và kiểm tra

- Dữ liệu gốc và pipeline output: `artifacts/session-w03-2026-11-13/`.
- Đồ thị: `w03-evaluation.png`; dự báo vẽ theo thời điểm nhãn tương lai, không theo thời điểm phát dự báo.
- Nhật ký, chất lượng, kết quả và checksum: `docs/w03-evidence/`.
- MAE được tính lại từ CSV dự báo; checksum candidate đối chiếu thành công; các file trong manifest W01 giữ nguyên.
- Chưa commit/push W03, chưa bật điều khiển AI.
