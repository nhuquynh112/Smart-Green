# Phiếu đo lưu lượng bơm — chưa thực hiện

Dùng sau khi phiên thu kết thúc và các bước chuẩn bị trong [checklist phần cứng](TV1_HARDWARE_ACCEPTANCE.md) đã đạt. Phiếu trống không phải kết quả hiệu chuẩn; không bật bơm chỉ vì đã điền tài liệu.

## Thông tin buổi đo

- Ngày giờ có múi giờ / người đo:
- Device ID / commit firmware / calibration ID:
- Nguồn và điện áp đo tại tải:
- Loại bơm / ống (chiều dài, đường kính) / đầu tưới:
- Chênh cao bình nước–đầu ra / mực nước ban đầu:
- Bình đong và độ chia nhỏ nhất / cách đo thời gian:
- Giới hạn xung đã được phép thử / khoảng nghỉ:
- Tệp ảnh, video, log:

Giữ cấu hình đường nước nhất quán giữa các phép đo. Dẫn nước vào bình đong có khay hứng, không dùng cây để thử lượng nước. Chọn xung ngắn trong giới hạn đã kiểm tra, không tăng thời gian chỉ để dễ đong. Ghi rõ ống đã đầy nước hay còn không khí; tách các điều kiện khác nhau thành nhóm đo riêng.

## Số đo thực tế

| Lần | Thời điểm | Xung yêu cầu (ms) | Thời gian chạy đo được (s) | Lượng nước (ml) | Còn chảy sau OFF? | Điều kiện / bất thường |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

Ghi cả phép đo không đạt, lượng nước bằng 0 hoặc không đo được; không xóa để làm đẹp kết quả. Nếu cần loại một phép khỏi tính lưu lượng, ghi lý do và giữ bản gốc. Không thay thời gian đo bằng xung yêu cầu khi chưa xác minh chúng khớp nhau.

## Tính toán và kết luận

- Lưu lượng từng lần: lượng nước / thời gian thực đo (ml/s).
- Lưu lượng chung: tổng lượng nước / tổng thời gian; không lấy trung bình đơn giản khi thời gian các lần khác nhau.
- Ghi min/max, biến động giữa các lần và sai số dụng cụ. Thời gian khởi động, không khí trong ống, điện áp và chênh cao có thể làm kết quả thay đổi.
- Ước tính thời gian cho lượng nước mong muốn chỉ là tham khảo, không tự trở thành maxPulseMs, cooldown hoặc quota.
- Chảy tiếp sau OFF, phao không ngắt hoặc nguồn làm ESP32 reset: ghi chưa đạt và xử lý trước khi thử tiếp trên cây.

Kết quả tính:

- Tổng ml / tổng s / ml mỗi giây:
- Khoảng lưu lượng quan sát / độ phân tán:
- Phạm vi điều kiện áp dụng:
- Giới hạn đề xuất và căn cứ (chưa kích hoạt):
- Người kiểm tra / đạt hoặc chưa đạt / việc phải sửa:

## Công cụ đã có

`tools/calibration.py` hỗ trợ template và phân tích hồ sơ gồm cả hiệu chuẩn đất lẫn lưu lượng. Chỉ dùng khi có đủ số đo thật; không lặp lại 2511 hoặc 979 năm lần để giả làm năm phép đo đất. Công cụ yêu cầu ít nhất ba phép đo bơm dương, nên phép đo 0 ml/không hợp lệ phải được giữ trong phiếu và xử lý nguyên nhân riêng.

Chạy từ thư mục gốc repo, sau buổi thử:

```bash
python3 tools/calibration.py template --output data/calibration-measured-new.json
# Điền số đo thực tế vào file mới, rồi phân tích:
python3 tools/calibration.py analyze data/calibration-measured-new.json --output-dir artifacts/calibration-measured-new
```

File/folder phải mới. Báo cáo và site_config.draft.h chỉ là bản nháp; công cụ không tự cho phép chạy bơm hoặc thay site_config.h đang dùng. Không ghi Wi-Fi/API key vào phiếu.
