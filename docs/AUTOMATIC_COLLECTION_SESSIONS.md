# Phiên thu với mốc thời gian tự động

Hoàn thiện ngày 15/11/2026. Mục tiêu: giảm nhập tay khi phân phiên dữ liệu, không điều khiển bơm và không tự huấn luyện AI.

## Sử dụng

1. Đăng nhập quản trị, chọn thiết bị rồi bấm **Bắt đầu phiên ngay**. Backend tự đặt tên (có thể sửa), ghi giờ UTC từ server và lấy mã hiệu chuẩn mới nhất của dữ liệu thật hoặc của thiết bị. Giờ trên biểu mẫu hiển thị theo múi giờ trình duyệt.
2. Khi đóng trang, việc thu cảm biến vẫn tiếp tục miễn là thiết bị, mạng và backend hoạt động. Khi mở lại, bấm **Tải danh sách phiên** để trở về phiên đang thu.
3. Nếu tưới tay, mất điện hoặc có khoảng không theo dõi, bổ sung nhật ký và bấm lưu. Không biết lượng nước thì để trống, không nhập số ước lượng như thể tích thực đo.
4. Bấm **Kết thúc phiên**: server ghi giờ kết thúc. Nếu còn chỉnh sửa chưa lưu, giao diện yêu cầu lưu trước. Kiểm tra nhật ký, xác nhận lịch sử nếu thực sự đầy đủ rồi lưu và xuất ZIP.

Tự động ở đây là tự tạo/lưu mốc bắt đầu–kết thúc khi bấm nút. Chưa có hẹn giờ tự kết thúc; chưa tự phát hiện tưới tay, nhập sự kiện bơm vào nhật ký hoặc tự huấn luyện. Không coi việc kết thúc phiên là xác nhận đầy đủ lịch sử. Lần tưới trước phiên để trống đến khi người thu xác nhận, không suy diễn từ bản ghi chạy bơm.

## Tính nhất quán

- ID khởi tạo được lưu tại trình duyệt trước khi gửi; gửi lại cùng ID trả về phiên cũ, không đổi giờ bắt đầu.
- Mỗi thiết bị tối đa một phiên đang mở; thao tác sửa/kết thúc dùng revision để không ghi đè bản mới.
- Gửi lại kết thúc sau mất phản hồi giữ nguyên mốc đã lưu.
- Mọi endpoint cần quyền quản trị; tạo/kết thúc không ghi vào hàng đợi lệnh và không sửa telemetry.
- Dữ liệu xuất theo received_at trong `[start,end)`; đóng phiên chỉ chốt phạm vi, không ngắt việc nhận telemetry.

## Kiểm chứng

- `pytest backend/tests -q`: **100 passed**, có PostgreSQL 16 UTF-8 tạm riêng; không dùng database production.
- `node backend/tests/dashboard_controls.test.cjs`: **21 passed**, gồm thử mất phản hồi, giữ ID yêu cầu và bảo vệ nhật ký chưa lưu.
- Chưa nghiệm thu trực tiếp bằng trình duyệt thật hoặc ESP32. Không có thay đổi firmware.

Mã đã ghép trong working tree. Chưa restart backend hoặc commit/push cho bản sửa này. Các nút mới cần backend mới được khởi động lại ngoài phiên thu. Backup hiện trạng trước khi triển khai theo tài liệu POST_W04_INTEGRATION_2026-11-14.md.
