# Rà soát luồng điều khiển — 10/11/2026

Phạm vi: dashboard, API lệnh/ACK, firmware controller/network/telemetry, lịch sử bơm và hạn mức. Không gửi lệnh tới bơm thật, không xóa dữ liệu hoặc bộ đếm NVS.

## Các lỗi đã sửa

| Vấn đề | Hành vi sau sửa |
|---|---|
| Polling ghi đè lựa chọn chế độ | Giữ lựa chọn, hiển thị trạng thái xác nhận riêng |
| Bấm lặp tạo nhiều lệnh | Chặn lệnh đồng thời trên UI và dưới transaction backend; STOP/OFF vẫn được gửi |
| ACK đổi chế độ đến trước telemetry | Hiển thị ACK đúng, chờ mẫu mới trước khi mở tưới |
| HTTP 204 bị đọc body | Firmware bỏ đọc body 204; polling 1 giây |
| Thay đổi điều khiển đợi chu kỳ 30 giây | Gửi telemetry khi chế độ, bơm, số lệnh đổi |
| Hết quota nhưng nút còn sẵn sàng | Firmware gửi quota thực, UI khóa theo số lần và thời lượng yêu cầu, backend kiểm tra lại |
| Mặc định backend 6 lần khác firmware 4 lần | UI dùng hạn mức ESP32; không giả định giới hạn khi thiếu dữ liệu |
| Dữ liệu cũ/clock/storage/pump không được kiểm tra đủ | Backend từ chối WATER khi chưa MANUAL, stale, chưa commissioning, lỗi clock/storage, đang bơm hoặc hết quota/cooldown |
| STOP đứng sau lệnh chờ | STOP/OFF đánh dấu lệnh pending trước đó hết hiệu lực; lệnh mới vẫn phải được ESP32 nhận |
| STOP hết hạn tắt rồi AUTO có thể bật lại | Controller đưa về OFF trước kiểm tra TTL; cả OFF và STOP được phép tắt khi clock chưa đồng bộ |
| Ước tính ml gây hiểu nhầm | UI hiển thị chưa hiệu chuẩn khi chưa có lưu lượng cấu hình |
| Thử bơm bị gọi là tưới cây | Đổi nhãn thành lịch sử chạy bơm; cần nhật ký để biết đích nước |

## Quy tắc hiện tại

- MANUAL không cooldown theo yêu cầu; AUTO 10 phút. Không biến MANUAL thành chạy liên tục: mỗi lệnh vẫn có thời lượng.
- Giới hạn thiết bị hiện tại: 1 giây/xung, 4 lần/cửa sổ 24 giờ và 4 giây thời lượng đã dành. Thời lượng đã dành có thể lớn hơn thời gian chạy thực tế vì không hoàn lại khi dừng sớm/reset.
- Cửa sổ bắt đầu từ lần bơm đầu tiên, không phải reset lúc 0 giờ. Bộ đếm giữ qua reboot/nạp. Không tự tăng quota hoặc xóa lịch sử để phục vụ thử.
- STOP là lệnh qua mạng, không thay thế ngắt nguồn trực tiếp. Lệnh đã đến ESP32 có thể đã thực thi trước khi server nhận STOP; timer, phao và giới hạn tại thiết bị vẫn là lớp chặn cuối.
- ACKED nghĩa là đã nhận kết quả, không đồng nghĩa bơm thành công. `started` mới là bắt đầu; event là bản ghi kết thúc. `cooldown`, `quota`, `expired_or_clock` là từ chối.
- Bản ghi bơm không chứng minh đã có nước chảy hoặc nước vào cây. Chưa có cảm biến lưu lượng; không dùng ml ước tính làm dữ liệu đo.

## Triển khai và thử sau

1. Rút adapter trước khi nạp; đóng Serial Monitor. Nạp firmware có `control_revision=reviewed-controls-v3`.
2. Restart tiến trình backend để tải thay đổi Python, tải lại trang để nhận HTML mới. Không chạy seed_demo trên DB thật.
3. Chưa cấp nguồn bơm: xác nhận quota hiển thị đúng 4 lần/4 giây, MANUAL không cooldown, phao đủ/thiếu cập nhật đúng.
4. Kiểm tra một lệnh đổi chế độ được ACK; không có lệnh tồn trước thử nước.
5. Khi còn quota và đã chuẩn bị cốc đong, thử một xung có giám sát, đối chiếu ACK, event, thời lượng và lượng nước đo thật. Nếu quota đã hết, không cố bấm lại hoặc reset để vượt quota; cần chốt cấu hình thử riêng và giới hạn phù hợp trước.

## Giới hạn kiểm chứng

Kiểm thử tự động dùng SQLite và ASGI trong bộ nhớ, controller C++ trên host, DOM giả lập và build ESP32. Chưa nạp bản review cuối, chưa restart server đang chạy, chưa kiểm thử vật lý và chưa chạy test cạnh tranh transaction trên PostgreSQL thực. Cần đo độ trễ sau nạp, kiểm chứng mất Wi-Fi/STOP/tank trên thiết bị thật với adapter được quản lý tại chỗ. Không tuyên bố hết mọi lỗi phần cứng hay đã hiệu chuẩn lưu lượng.

## Điều chỉnh cho phiên thử vào cốc

Người dùng xác nhận thử vào cốc và yêu cầu tăng hạn mức. Cấu hình riêng của máy trong site_config.h được tăng lên 20 lần / 20000 ms mỗi cửa sổ 24 giờ; mỗi xung vẫn tối đa 1000 ms. Không thay đổi mẫu mặc định, không xóa bộ đếm NVS hay lịch sử. Đây là giới hạn thử có giám sát, chưa phải định mức tưới cây. Cần nạp lại để áp dụng, kiểm tra dashboard phản ánh hạn mức mới trước khi cấp nguồn bơm.
