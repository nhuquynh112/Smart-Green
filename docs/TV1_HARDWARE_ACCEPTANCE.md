# TV1 — Kịch bản nghiệm thu khi lấy phần cứng ra

Cập nhật 08/11/2026. Đây là **kế hoạch kiểm tra**, chưa phải biên bản đạt. Bản bringup đã thử phần cứng cơ bản; runtime vẫn cần các bước dưới đây.

## Trước buổi thử

- Ghi commit, board thực tế, cấu hình (che Wi-Fi/API key), nguồn, ảnh dây và vị trí cảm biến.
- Chuẩn bị bình đong, khay hứng, đồng hồ đo/thời gian và cách ngắt nguồn bơm dễ tiếp cận.
- Giữ `SG_AI_COMMANDS_ENABLED=false`. Không bật cờ commissioning chỉ vì code build được.
- Kiểm tra mức kích relay: bringup hiện dùng `RELAY_ACTIVE_LOW=false`, trong khi runtime mặc định `SG_RELAY_ACTIVE_LOW=true`. **Phải xác minh và cấu hình đúng mức kích trước khi nối bơm vào runtime.** Hai bản không tự chia sẻ cấu hình này.
- Hiệu chuẩn bench trong NVS không tự chuyển sang runtime. Nhập mốc đã xác minh và calibration ID vào `site_config.h` cục bộ; không commit mật khẩu.
- Giai đoạn A kiểm tra relay/output với nguồn tải bơm được ngắt; giai đoạn B mới nối bơm và dẫn nước vào bình đong, có người giám sát. Chỉ sau khi B đạt mới thử trên cây.

## A. Runtime và backend, chưa cấp nguồn tải bơm

| ID | Thao tác | Kết quả cần quan sát | Bằng chứng |
| --- | --- | --- | --- |
| A01 | Kiểm tra mức điều khiển khi bật nguồn, reset và nạp firmware | Relay ở OFF; không có xung ON ngoài ý muốn | Video và mức điện đo được |
| A02 | Đối chiếu 4 cảm biến và hiệu chuẩn runtime | GPIO đúng, soil_pct hợp lý, invalid dùng null, phao đúng trạng thái | Telemetry + cấu hình không chứa bí mật |
| A03 | Boot khi chưa có Wi-Fi/NTP | Không chấp nhận lệnh bật khi chưa biết giờ | clock_ready, ACK từ chối |
| A04 | Kết nối backend TV2 | Telemetry lưu đúng identity, giờ đo/nhận riêng | Request, response, hàng DB |
| A05 | Gửi lại cùng telemetry và bản xung đột | Bản trùng không nhân đôi, xung đột không ghi đè | Số hàng DB và HTTP status |
| A06 | Thử SET_MODE/STOP, sai device, sai key, lệnh hết hạn | Đúng lệnh được ACK, sai lệnh không kích output | command_seq + ACK |
| A07 | Mất phản hồi ACK rồi gửi lại lệnh | Không phát sinh lần tưới thứ hai; đối chiếu event thay vì coi duplicate là success | Sequence và event log |
| A08 | Cho backend phản hồi chậm/ngắt kết nối | Vòng cảm biến/guard không bị chặn; OFF/MANUAL không tự chuyển AUTO | Log theo thời gian |

Dùng môi trường thử và sequence mới. Không xóa NVS để vượt hạn mức. Các bài kiểm thử software đã có không chứng minh flash, Wi-Fi, GPIO và lịch task thật hoạt động đúng.

## B. Bơm vào bình đong, có giám sát

| ID | Thao tác | Kết quả cần quan sát | Bằng chứng |
| --- | --- | --- | --- |
| B01 | Thử xung ngắn trong giới hạn đã cấu hình | Bơm dừng, đo thời gian và lượng nước; kiểm tra nước còn tự chảy sau OFF | Ít nhất 3 phép đo độc lập, ml và ms |
| B02 | Phá điều kiện đủ nước trước lệnh và trong lúc bơm | Từ chối khởi động hoặc ngắt khi phao thiếu nước | tank_ok, thời gian ngắt, video |
| B03 | Yêu cầu thời gian vượt maxPulseMs và tưới lại trước cooldown | Từ chối; không có nước thêm | Lệnh/ACK và đo thực tế |
| B04 | Đạt hạn mức số lần/thời gian trong cửa sổ cấu hình | Lệnh tiếp bị chặn; reset không xóa hạn mức | Event log trước/sau reset |
| B05 | Reset giữa một xung thử có giới hạn | Output về OFF, Reboot ghi actual_ms không biết, không lặp lệnh | Video + event + NVS state quan sát |
| B06 | Thử lỗi cảm biến qua quy trình có kiểm soát | Giá trị invalid/stale không được dùng để bật bơm | raw, valid flags, ACK |
| B07 | Tạo lỗi mạng/HTTP trong khi bơm | Xung vẫn bị ngắt theo giới hạn; đo độ trễ thực tế | Thời gian thực đo, log mạng |
| B08 | Event queue đầy trong cấu hình thử đã xem xét | Khóa lần tưới mới cho tới khi sự kiện được ACK | Số event, lý do từ chối |

Không chập dây để tạo lỗi. Muốn thay đấu nối phải ngắt nguồn phù hợp. Không kéo dài bơm chỉ để đủ số đo; chọn thời gian thử theo phần cứng đã xác minh. Timer phần mềm không xử lý được mọi lỗi relay dính hoặc CPU treo hoàn toàn.

Quota hiện là cửa sổ 24 giờ cố định từ lần tưới đầu, không phải cửa sổ trượt. Cần kiểm tra sát ranh giới quota bằng cấu hình kiểm thử có ghi lại, không thử lượng nước lớn lên cây.

## C. Auto-Rule, dữ liệu và AI

| ID | Công việc | Điều kiện đạt |
| --- | --- | --- |
| C01 | Chọn ngưỡng thấp/cao, xung và khoảng nghỉ từ cây/đất/lưu lượng | Có lý do lựa chọn và số đo; không dùng mặc định làm kết luận |
| C02 | Kiểm tra hysteresis và ba mẫu khô liên tiếp | Không bật/tắt liên tục quanh ngưỡng; dừng/khóa đúng điều kiện |
| C03 | Thử AUTO mất mạng sau khi có giờ; boot không mạng | Phân biệt đúng hai tình huống; khóa khi chưa có giờ hợp lệ |
| C04 | Thu nhiều chu kỳ khô–tưới có nhật ký | CSV có thời gian rõ, khoảng thiếu đánh dấu, một calibration/session |
| C05 | Đánh giá AI trên dữ liệu thật | Chia thời gian, so baseline, báo MAE; đủ chu kỳ được phân tích riêng |
| C06 | Chạy AI chỉ quan sát | Lưu đề xuất và so thực tế; không tự cấp quyền điều khiển |
| C07 | Demo toàn hệ thống | Dashboard/DB/ESP32 thống nhất trạng thái, các giới hạn vẫn có hiệu lực |

## Mẫu ghi một phép thử

Sao chép cho từng ID, lưu cùng video/log trong thư mục dữ liệu cục bộ:

```text
Test ID:
Người thực hiện / người quan sát:
Thời gian bắt đầu/kết thúc có múi giờ:
Commit firmware / commit backend / board:
Cấu hình giới hạn (không chứa bí mật):
Điều kiện ban đầu:
Các bước thực hiện:
Kết quả mong đợi:
Kết quả thực đo (ml, ms, GPIO, HTTP/ACK):
File log / video / ảnh:
Đạt / Không đạt / Chưa thử:
Lỗi và cách khắc phục:
Ngày thử lại:
```

Tất cả các mục runtime ở tài liệu này mặc định **chưa thử trên phần cứng**. Sau mỗi phép thử, ghi bằng chứng trước khi đổi trạng thái.
