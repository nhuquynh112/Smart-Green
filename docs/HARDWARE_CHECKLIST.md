# Checklist khi mua và nhận linh kiện

Cập nhật 04/11: đã chốt nhóm linh kiện ESP32 DevKit 30 chân, DHT22, LDR, đất điện dung, relay và phao; chưa có mã sản phẩm cụ thể. Pin map dự kiến và quy trình nạp bench nằm trong [TV1_TOMORROW.md](TV1_TOMORROW.md). Gửi link/ảnh trước mua để kiểm tra tương thích; không suy chân/điện áp chỉ từ tên “ESP32” hay “relay 5V”.

## Thông tin cần cung cấp

- Board ESP32: tên chip, tên board, ảnh hai mặt, loại USB.
- Cảm biến đất điện dung: model, điện áp cấp và dải điện áp analog ra.
- DHT22 hoặc BME280: chọn một; xác định module có sẵn pull-up/đổi mức hay chưa.
- BH1750 nếu cần lux; LDR chỉ dùng chỉ số tương đối nếu chưa hiệu chuẩn quang.
- Bơm DC: điện áp, dòng chạy và dòng khởi động theo nhà bán/datasheet; ống, độ cao nâng và bình nước.
- Relay/MOSFET: điện áp logic, mức kích, dòng tải DC, cấu hình OFF khi reset.
- Nguồn phù hợp bơm và board, dây/đầu nối, phần bảo vệ tải cảm theo module thực tế.
- Cảm biến/phao mức nước nếu nghiệm thu khả năng phát hiện hết nước.
- Chậu, loại cây, đất, khay hứng; bình đong và đồng hồ đo điện để hiệu chuẩn/kiểm tra.

## Hiệu chuẩn đất

Lưu raw ADC trước khi ánh xạ. Lấy mẫu lặp ở đất khô tham chiếu và đất đã tưới rồi thoát nước ổn định, cùng độ sâu/vị trí; ghi điều kiện thay vì gọi đó là độ ẩm tuyệt đối. Kiểm tra chiều tín hiệu, độ phân tán, dải hữu dụng. Công thức hai điểm chỉ là chỉ số tương đối, có thể phi tuyến. Chọn ngưỡng từ quan sát cây/đất và đo kiểm, không dùng ngay 30/45 trong code vì đó là số thử logic.

Với ESP32 cổ điển, lựa chọn chân ADC cần xét hoạt động Wi-Fi; kiểm tra datasheet đúng biến thể và giới hạn đầu vào. [Tài liệu ADC Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html).

## Hiệu chuẩn bơm

Thử ngắn có giám sát với đúng ống và độ cao thực tế; đo thể tích/thời gian nhiều lần, ghi độ phân tán. Ước lượng lưu lượng Q=V/t; chọn thời gian xung, nghỉ ngấm và hạn mức từ đo thực tế. Thể tích suy ra từ thời gian là ước lượng, không phải đo trực tiếp nếu không có flow sensor. Kiểm tra nước tiếp tục chảy sau tắt do siphon. Không lấy thời gian giới hạn từ repo khác.

## Kiểm thử phải làm trước vận hành

| Tình huống | Hành vi cần xác nhận | Bằng chứng |
|---|---|---|
| Boot/reset khi relay nối | Bơm OFF, không có xung bật ngoài ý muốn | Video/đo mức điều khiển |
| Tắt mạng/server treo | AUTO vẫn an toàn; OFF giữ OFF | Log trạng thái + thời gian |
| Rút cảm biến/giá trị bất thường | Dừng/chặn tưới, báo lỗi | Raw + cờ lỗi |
| Bồn hết nước/đứt dây mức nước | Dừng/chặn theo mạch đã chọn | Video + log |
| Lệnh trùng/hết hạn/sai device | Không tưới thêm | Lệnh + ACK + sự kiện |
| Quá thời gian bơm | Ngắt độc lập với HTTP; đo sai lệch | Thời gian đo thật |
| Nguồn bơm gây sụt áp/reset | Khởi động an toàn, quota không bị xóa | Điện áp + log boot |
| Restart giữa lần tưới | Nhật ký đánh dấu thời gian không rõ | Sự kiện Reboot |
| Chạy 24 giờ | Báo tỷ lệ thiếu, số lần tưới, lỗi và phục hồi | CSV + báo cáo |

Đạt test phần mềm không thay thế các thử nghiệm này. Chưa xác định phần cứng thì chưa chốt pin map, sơ đồ dây hay giới hạn bơm vận hành.
