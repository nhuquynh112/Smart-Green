# Hoàn thiện mục 1–3 — 16/11/2026

## Đã sửa trong source

- Không có mật khẩu quản trị dự phòng. SG_WEB_PASSWORD thiếu/rỗng: HTTP 503 cho thao tác quản trị; không chặn telemetry/device API. Mật khẩu đã cấu hình vẫn giữ nguyên, không in/đọc secret live. Basic Auth cần HTTPS khi triển khai ngoài mạng demo tin cậy; nhiệm vụ này chưa dựng TLS cho máy thật.
- Chart.js 4.4.7 + MIT license đóng gói nội bộ, bỏ tải font ngoài. Không cần Internet để tải thư viện biểu đồ. Metadata AI và chú thích nguồn thực/synthetic nhất quán. Xu hướng ADC không còn kết luận sáng/tối từ một dao động nhỏ.
- AI real yêu cầu chọn phiên đã kết thúc/đối soát, revision hiện tại, calibration đúng, có lần tưới trước, không có khoảng không rõ. Chỉ dùng phút đầy đủ trong phạm vi được đối soát và boot hiện tại; inference vẫn chặn dữ liệu cũ. UI gửi ID/revision của phiên đã chọn, chặn bản nháp chưa lưu.
- Kết hợp tưới tay từ journal và sự kiện bơm trong DB. Bản journal phương pháp pump phải khớp chính xác mốc DB, không cộng hai lần; tưới tay chồng bơm bị từ chối. Không tự sửa nhật ký/DB.
- Reboot cũ trước mốc tưới đã biết không còn chặn mãi. Reboot hoặc thời lượng không rõ sau mốc đó vẫn từ chối. Sự kiện bơm ngoài phạm vi lịch sử đối soát phải được làm rõ; không bỏ qua để ép dự báo.
- Giữ độ chính xác phần giây của sự kiện bơm khi tạo đặc trưng; không làm tròn xuống giây nguyên.

## W05

Đã xử lý sau xác nhận người dùng, không fit/tuning trên W05. RF có ánh sáng MAE 4,0256/4,2872; Persistence 0,8034/1,4411 cho 30/60 phút. 418/388 cửa sổ chung. Không thay model production. Xem W05_REVIEW_2026-11-15.md và bộ artifact session-w05-2026-11-15. W05 cùng chu kỳ tưới W04, không gọi là chu kỳ độc lập.

## Kiểm thử

- Python AI/backend/tools: 168 passed, 7 skipped, 8 subtests passed; PostgreSQL variants chưa chạy lại trong lượt này.
- Sau khi tăng độ chặt test route (kiểm tra đủ 16 phút thay vì chỉ fake predictor), 8 test route/reconciliation đạt.
- Dashboard: 24 passed, gồm local asset, nhãn real/synthetic, chống ID trùng và luồng điều khiển cũ.
- Kiểm tra evaluator tái tạo MAE W04; đối chiếu MAE W05 từ CSV, giữ checksum model và input nguồn. Không nạp firmware, không chạy thử bơm.
- Lượt test đầu có 1 lỗi kỳ vọng HTTP 401 vì test chưa cấu hình password; test đã đặt mật khẩu riêng tường minh, không phục hồi mật khẩu mặc định để làm test qua.

## Đưa vào sử dụng

1. Ngoài phiên thu, sao lưu DB và bảo đảm tiến trình backend có SG_WEB_PASSWORD do người quản trị chọn; không lưu vào Git.
2. Restart backend theo cách đang vận hành để nhận API mới; Ctrl+Shift+R cho UI. Chỉ đổi file HTML khi API cũ còn chạy chưa đủ để nghiệm thu tính năng mới.
3. Thử đăng nhập, tạo/kết thúc/lưu/đối soát/chọn một phiên thử, xuất ZIP. Dự báo online cần dữ liệu mới (độ tuổi theo inference tối đa 120 giây); phiên cũ dùng đánh giá offline, không sửa giờ dữ liệu.
4. Thử offline bằng ngắt Internet trong mạng LAN vẫn kết nối backend; xác nhận biểu đồ tải từ /static/vendor. Chưa xác nhận bằng trình duyệt thật trong lượt này.

Không restart backend hay can thiệp dữ liệu đang thu trong nhiệm vụ này. Chưa commit/push. Firmware, AUTO và quyền điều khiển của AI không thay đổi. AI thử nghiệm ánh sáng chỉ offline.
