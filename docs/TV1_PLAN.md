# Kế hoạch TV1 và đánh giá tổng quát

## Phạm vi đã thống nhất

Cập nhật 06/11/2026: đã kiểm tra tín hiệu bốn cảm biến bằng bringup; relay/bơm và hiệu chuẩn đất còn chờ. Runtime IoT đã viết/build và kiểm thử offline theo TV1_RUNTIME.md; chưa nạp bản runtime lên thiết bị. Không mặc định ngày mua là ngày bắt đầu kế hoạch 14 ngày. Không có bằng chứng hiện tại để khẳng định hoàn thành phần cứng hay AI thực nghiệm.

Kiến trúc một chậu, ESP32 tự quyết định an toàn; FastAPI/PostgreSQL/Web do TV2 phụ trách; TV1 sở hữu cảm biến, điều khiển, dữ liệu đầu vào, huấn luyện và đánh giá AI. Hai bên cùng chịu trách nhiệm API, xác nhận thực thi và kiểm thử toàn hệ thống.

## Các điều chỉnh cần đưa vào kế hoạch gốc

1. Ngày 6 chỉ cam kết pipeline AI hoạt động, chưa cam kết thắng baseline. Số dòng/phút không thay thế số chu kỳ khô–tưới độc lập.
2. Dự đoán độ ẩm tương đối sau 30 phút **nếu không tưới thêm**. Chỉ mở rộng 60 phút khi dữ liệu hỗ trợ. Không gọi chỉ số 0–100 là độ ẩm thể tích.
3. Auto-Rule luôn là nền an toàn trong AUTO; mất mạng không làm mất nó. OFF/MANUAL không tự đổi sang AUTO khi mất mạng. Đây là làm rõ yêu cầu mất liên lạc 60 giây.
4. AI chỉ đề xuất tưới sớm; phải kiểm tra cảm biến mới, mức nước, thời gian nghỉ, giới hạn xung và hạn mức trước khi thực thi.
5. Bổ sung phương án phát hiện hết nước vào BOM hoặc bỏ tiêu chí tự phát hiện. Chưa có phần cứng thì không được giả định `tankOK=true` trong bản vận hành.
6. Kiểm thử từng phần từ đầu; ngày 12 dành cho nghiệm thu tổng thể. Báo cáo viết dần, không để toàn bộ tới ngày 13.

## Trình tự sau khi có linh kiện

| Mốc | TV1 thực hiện | Điều kiện hoàn thành |
|---|---|---|
| 1 | Kiểm tra BOM, nguồn, chân, chốt API với TV2 | Có sơ đồ theo đúng linh kiện thật |
| 2–3 | Driver cảm biến, hiệu chuẩn, thử bơm ngắn có giám sát, thu dữ liệu | Có log raw + hiệu chuẩn + bản tin nhận ở backend |
| 4–5 | Auto-Rule, thời gian nghỉ, giới hạn bơm, lỗi cảm biến/nguồn | Các tình huống an toàn được đo kiểm |
| 6–7 | Kiểm tra dữ liệu, baseline, mô hình đầu | Chạy lại được bằng lệnh, có báo cáo chất lượng dữ liệu |
| 8–9 | Đánh giá theo thời gian, lựa chọn bằng validation, tích hợp hàm predict | Có test riêng chưa dùng chọn mô hình |
| 10–11 | AI ở chế độ quan sát, xét điều kiện kích hoạt, tích hợp ACK | Chống trùng/hết hạn/reset có bằng chứng |
| 12–14 | Nghiệm thu, số liệu thật, video, báo cáo | Phân biệt rõ đạt/chưa đạt và giới hạn |

## Giới hạn của bản khung hiện tại

- Đã có driver GPIO/cảm biến, HTTP/NTP, guard timer task; chưa nghiệm thu trên mạch hoặc backend thật. Guard không phải mạch ngắt nguồn phần cứng.
- Hạn mức là cửa sổ 24 giờ bắt đầu tại lần tưới đầu tiên, **không phải** mọi cửa sổ trượt 24 giờ. Phải đánh giá giới hạn sát ranh giới cửa sổ trước khi nghiệm thu.
- Reset sẽ tắt trạng thái pumping, giữ phần thời gian đã dự trù và chờ lại đủ cooldown. Chưa biết giờ UTC sau khởi động thì khóa tưới. Cần chọn giải pháp giờ cho mất điện+mất mạng: RTC hoặc quy trình khởi động lại có giám sát.
- Khi reset giữa lần tưới, thời gian thực tế là không biết, sự kiện có reason Reboot; không diễn giải actualMs=0 là không tưới.
- Nhật ký 32 sự kiện đầy sẽ chặn lần tưới mới; cơ chế gửi/ACK đã viết nhưng còn phải thử với backend và mất mạng dài ngày.
- `tick()` phải được gọi thường xuyên. Giới hạn thời gian trong core không bảo vệ được khi task bị treo; trước nối bơm cần bộ ngắt/giám sát độc lập, mức OFF phần cứng và đo độ trễ.
- Lưu cấu trúc NVS là định dạng prototype, không phải định dạng nâng cấp bền vững; thay layout phải đổi version và có quy trình chuyển dữ liệu, không xóa hạn mức âm thầm.

## Bằng chứng phải có khi bảo vệ

Sơ đồ điện thật; bảng hiệu chuẩn cảm biến và lưu lượng; dữ liệu raw; nhật ký tưới; cấu hình/version; script huấn luyện; bảng MAE với baseline; biểu đồ thực tế/dự đoán; biên bản lỗi; video; hướng dẫn chạy lại. Không lấy số liệu của repo tham khảo làm kết quả của nhóm.
