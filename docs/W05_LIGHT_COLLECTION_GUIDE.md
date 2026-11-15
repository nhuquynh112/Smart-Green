# W05 — kiểm tra ánh sáng và ghi nhận thực nghiệm

## Trước phiên

- Triển khai backend mới ngoài phiên thu, rồi tải lại trang. Không cần nạp firmware cho nhiệm vụ ánh sáng này.
- Xác nhận mode **OFF** trên thiết bị/dashboard, không bật AUTO. Giữ AI mới offline, không cấu hình bundle thử nghiệm vào runtime.
- Kiểm tra ngày giờ máy, trạng thái đồng bộ ESP32 và ADC có cập nhật. Mã hiệu chuẩn đất giữ nguyên; ghi lại nếu thực sự thay cảm biến/mạch/nguồn điện.
- Chọn **Bắt đầu phiên ngay** rồi đổi tên thành W05, lưu. Hệ thống tự lấy giờ server/mã hiệu chuẩn. Nhập lần tưới gần nhất nếu nhớ rõ; nếu chỉ biết gần đúng, ghi chú độ không chắc chắn, không tự xác nhận chính xác.

## Trong phiên

1. Thu một đoạn điều kiện bình thường trước tác động. Giữ vị trí cây và cảm biến ổn định.
2. Nếu thử che riêng cảm biến ánh sáng, ghi mốc **Bắt đầu che cảm biến**; khi bỏ che ghi **Bỏ che cảm biến**. Nút **Lấy giờ hiện tại** lấy giờ máy đang dùng, không phải sự kiện tự phát hiện. Bấm **Thêm mốc** và **Lưu phiên** để lưu vào database.
3. Nếu đổi đèn/vị trí chiếu sáng, ghi loại mốc tương ứng, mô tả thao tác và điều kiện. Không đồng thời đổi vị trí cây, tưới nước và che cảm biến rồi quy toàn bộ thay đổi soil cho ánh sáng.
4. Che cảm biến riêng chỉ kiểm tra chiều đáp ứng ADC; không đại diện việc thay đổi ánh sáng nhận được của toàn cây. Không kết luận quan hệ nhân quả từ thử này.
5. Tưới nếu có theo nhu cầu thực tế, ghi giờ bắt đầu/kết thúc riêng ở phần tưới. Chỉ nhập mL khi đo; lượng ước tính bằng muỗng ghi trong ghi chú. Không tưới chỉ để làm đẹp đường dữ liệu.
6. Mất điện/reset/di chuyển cây hoặc cảm biến: ghi mốc và ghi chú; khoảng không rõ lịch sử dùng mục tương ứng. Không sửa/mất dữ liệu gốc.

Mốc quan sát được lưu trong `observations` với `at`, `kind`, `note`. Có thể ghi nhiều mốc che/bỏ che; không tự biến thành sự kiện tưới hoặc lệnh ESP32. Mốc phải nằm trong thời gian phiên. Những mốc chưa lưu không xuất vào file ZIP.

## Kết thúc và xuất

- Lưu các chỉnh sửa, bấm **Kết thúc phiên**. Đối chiếu lịch sử rồi mới tích xác nhận đầy đủ và lưu lại.
- Xuất ZIP: có `journal.json` (gồm mốc quan sát), `session.json`, `telemetry.csv` với soil/nhiệt độ/độ ẩm/ADC và `database-rows.jsonl` giữ bản gốc.
- Giữ nguyên file xuất. Nếu ánh sáng thiếu hoặc chạm 4095, giữ và đánh dấu thay vì điền giả.
- Kết thúc phiên chỉ chốt phạm vi export `[start,end)` theo giờ nhận; không dừng ESP32 hay tưới.

## Kế hoạch đánh giá

Giữ model thử nghiệm ngày 15/11 cố định, W05 chưa dùng để fit/tuning. Đánh giá trên cùng cửa sổ cho mô hình có/không ánh sáng, Persistence, 30/60 phút. Kiểm tra độ đầy đủ, bão hòa, giờ mốc, thay đổi hiệu chuẩn và các cửa sổ có tưới trước khi tính MAE.

Sau khi đã xem kết quả W05, nếu dùng W05 để phát triển mô hình tiếp thì phải giữ phiên tương lai khác để kiểm định; không gọi lại W05 là test độc lập. Các cửa sổ trong cùng cây/chu kỳ không phải các thử nghiệm sinh học độc lập.
