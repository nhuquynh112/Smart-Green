# Điều tra ADC đất khi đổi phao — 23/11/2026

Người dùng xác nhận chưa gắn bơm, chỉ đẩy phao; không đang thu phiên. Không kết luận nhiễu motor hoặc lỗi dây. DB sau cập nhật ghi ADC ~2300 rồi 52/0/122 trong lúc thử phao; đây là raw đã nhận từ ESP32, không chỉ lỗi biểu đồ. Chưa chứng minh nguyên nhân.

Rà code: ADC đất GPIO34, phao GPIO26 INPUT_PULLUP. Sensor task đọc mỗi 1s qua queue sao chép; phần gửi phao không ghi soilRaw. Thay đổi gửi sớm dùng chung gói đầy đủ (cả soil), tăng tần suất HTTP và số mẫu nhìn thấy, nên chưa loại trừ tác động gián tiếp của thay đổi này. Native tests/build không kiểm chứng tính ổn định điện/ADC thực tế.

Bản đối chứng: `SG_FLOAT_FAST_TELEMETRY` mặc định false; chỉ vô hiệu trigger gửi phao, giữ periodic 30s, lịch/control publish, cách đo, calibration, URL và bảo vệ bơm. Log `# live` thêm soil_raw để so sánh độc lập với nhịp Dashboard; vẫn 3s/lần nên không đảm bảo bắt được mọi spike <3s. Không tự nạp.

Quy trình A/B có giám sát (bơm không kết nối, mode OFF):
1. Nạp bản đối chứng; giữ dây/vị trí cảm biến như trước. Không tạo phiên nghiên cứu.
2. Monitor 115200. Sau đồng bộ, để phao yên 60s, lưu log.
3. Đổi phao lên giữ 10s, xuống giữ 10s, lặp 3 lần; không kéo bó dây. Lưu log soil_raw/tank/boot hoặc reset.
4. Nếu raw vẫn tụt: chưa thể quy cho trigger gửi nhanh; tiếp tục kiểm tra đường đo với cùng phép thử. Nếu hết: mới là bằng chứng sơ bộ, cần lặp lại A trên cùng bố trí trước kết luận; không chỉ so độ mượt biểu đồ.
5. Không tăng lọc/đổi hiệu chuẩn hoặc xóa dữ liệu để che bất thường.

Hạn chế khác đã xác nhận: convert() chỉ loại ADC <=50 hoặc >=4045, còn 52/122 vẫn được clamp thành100%. Nhãn valid không chứng minh nằm trong vùng hiệu chuẩn 979–2511. Chưa đổi ngưỡng vì chưa có dữ liệu xác định margin đúng và không muốn trộn thay đổi vào phép thử A/B.

Kiểm thử bản đối chứng: native firmware PASS, AUTO 36 PASS, build esp32dev SUCCESS (không upload).
