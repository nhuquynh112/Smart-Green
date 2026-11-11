# Việc còn lại của TV1

## Mốc hiện tại — 11/11/2026 (ưu tiên hơn danh sách lịch sử bên dưới)

- Đã sửa luồng điều khiển, trạng thái dashboard và thời điểm tính xung; Python 97 tests + 8 subtests, dashboard 13 tests, native firmware đạt; ESP32 build/upload thành công.
- Đã nạp bản sửa và restart backend lúc khoảng 21:38; telemetry mẫu 2 xác nhận OFF, pump_running=false, clock_ready=true, không lỗi clock/storage. Chưa thử bơm thật trên bản vừa nạp.
- Phiên W01 đã xử lý: 1.062 mẫu trong 8 giờ 50 phút, 528 phút dùng được theo bộ lọc hiện tại. Xem [báo cáo W01](REAL_SESSION_W01_2026-11-11.md). Chưa đủ bằng chứng nhiều chu kỳ độc lập để kết luận AI tốt.

### Buổi test tiếp theo

1. Thử MANUAL cùng thời lượng 3 lần, hứng riêng từng lần và đo ml; quan sát motor dừng và không có nước tự chảy tiếp. Ghi command ID, thời lượng log và quan sát thật. 30–35 ml trước đây chỉ là ước lượng.
2. Xác minh STOP/OFF, phao thiếu nước, OFF sau reset; lưu bằng chứng. STOP qua mạng có độ trễ, ACK không phải cảm biến xác nhận motor.
3. Chốt chính sách hạn mức trước nghiệm thu AUTO: MANUAL bỏ giới hạn số lần nhưng vẫn dùng chung bộ đếm và ngân sách thời gian với AUTO. Không xóa NVS để vượt quota. Thử AUTO khô bật/đủ ẩm dừng, hysteresis, khoảng nghỉ và quota sau khi chính sách nhất quán.
4. Thử mất Wi-Fi/backend rồi phục hồi, lệnh trùng/hết hạn và reset; đối chiếu DB, ACK, mẫu thiếu và sự kiện, không chỉ nhìn dashboard.

### Để hoàn thành TV1

- [ ] Nghiệm thu phần cứng và điều khiển bằng bảng kết quả trên bản mới; cố định đường ống/cảm biến và đo lưu lượng.
- [ ] Xử lý chính sách quota chung và request dashboard treo; kiểm thử tích hợp PostgreSQL trên DB thử riêng cùng TV2.
- [ ] Thu thêm các chu kỳ khô–tưới độc lập với nhật ký; không dùng số giờ riêng lẻ làm tiêu chí đủ dữ liệu.
- [ ] Đánh giá baseline, Linear Regression, Random Forest bằng chia thời gian và tập test riêng; báo cáo MAE thật và giới hạn, không lấy MAE synthetic.
- [ ] Tích hợp dự báo ở chế độ quan sát, kiểm tra fallback; nghiệm thu phần phối hợp TV1/TV2.
- [ ] Hoàn thiện sơ đồ mạch thực tế, bảng hiệu chuẩn, biểu đồ, báo cáo, video và hướng dẫn chạy lại.

TV1 đang ở mốc tích hợp/nghiệm thu (nhóm ngày 10–12 trong kế hoạch); phần AI thực nghiệm ngày 6–9 và hồ sơ ngày 13–14 vẫn còn. Đây không phải xác nhận đã hoàn thành toàn bộ các ngày trước.

---

## Danh sách lịch sử ngày 08/11/2026

Cập nhật 08/11/2026. Danh sách dựa trên bằng chứng hiện có, không tính phần mềm offline là đã nghiệm thu phần cứng.

## Trong lúc phiên thu đang chạy

Có thể soạn báo cáo, tài liệu tích hợp và đọc mã nguồn. Giữ nguyên tiến trình thu, cổng Serial, firmware, cấu hình và file đầu ra đang ghi. Không mở thêm Monitor, upload hoặc bấm EN; giữ máy thức.

Đã có: parser, nhật ký tưới, builder dữ liệu phút, baseline/model, kiểm thử offline và báo cáo phiên 01. Không cần tạo thêm pipeline trùng chức năng.

## Sau khi phiên một giờ kết thúc — không cần TV2

- [ ] Đợi logger tự kết thúc; ghi lại số mẫu lưu và số dòng bỏ qua.
- [ ] Chạy parser với file phiên vừa kết thúc và output riêng.
- [ ] Đọc quality report: timestamp thiếu, identity trùng/xung đột, sequence, khoảng thời gian và trạng thái cảm biến.
- [ ] Ghi nhật ký tưới, reset, di chuyển cảm biến và khoảng không quan sát. Nếu không biết lần tưới trước thì để null.
- [ ] Đánh giá khả năng tạo dataset phút; không tự điền lịch sử thiếu để ép train.
- [ ] Tổng hợp kết quả vào báo cáo phiên mới; tiếp tục thu nhiều chu kỳ tự nhiên.

Với tên phiên hiện đang dùng, chạy **sau khi logger dừng** từ thư mục gốc repo:

```bash
python3 firmware/tool/parse_logs.py firmware/data/telemetry-session02.jsonl --output firmware/data/prepared/telemetry-session02.csv
```

Khoảng một giờ, chu kỳ 30 giây thường có xấp xỉ 120 mẫu; dùng timestamp và khoảng trống để đánh giá, không chỉ dựa vào số lượng. Dòng `# live` bị bỏ qua là bình thường. Xem [quy trình nhật ký và dataset](WATERING_AND_AI_DATASET.md).

## Hoàn thành truyền dữ liệu ESP32 → PostgreSQL — cần TV2

- [ ] TV2 cung cấp URL, device ID, cách xác thực và phản hồi theo contract; bí mật điền local.
- [ ] Sau phiên thu, cấu hình và thử gửi telemetry thật mỗi 30 giây.
- [ ] Đối chiếu identity, timestamp và giá trị giữa ESP32 và PostgreSQL; xác nhận ACK sau lưu bền.
- [ ] Gửi lại cùng identity không sinh bản ghi trùng.
- [ ] Thử mất mạng/phục hồi, ghi số mẫu bị mất và giới hạn queue; không yêu cầu queue hiện tại làm điều chưa hỗ trợ.
- [ ] Lưu bằng chứng và cập nhật trạng thái tích hợp sau khi đạt toàn luồng.

## Cần phần cứng và giám sát — làm sau phiên thu

- [ ] Kiểm tra OFF lúc boot/reset, mức kích relay và phao trên firmware runtime.
- [ ] Đo lưu lượng bơm bằng bình đo; chọn xung, khoảng nghỉ và hạn mức từ kết quả thật.
- [ ] Thử cạn nước, cảm biến lỗi, mất mạng, reset và lệnh trùng/hết hạn theo checklist.
- [ ] Cố định ống, phao và cảm biến; kiểm tra thoát nước, cách điện và bảo vệ mạch.
- [ ] Chỉ mở điều khiển/tưới tự động sau khi các điều kiện nghiệm thu đạt.

Chi tiết và cách ghi bằng chứng: [nghiệm thu phần cứng](TV1_HARDWARE_ACCEPTANCE.md).

## AI và báo cáo cuối

- [ ] Có dữ liệu thật đủ nhiều chu kỳ, nhật ký rõ ràng và tập đánh giá theo thời gian.
- [ ] Đánh giá baseline và model bằng MAE; ghi phạm vi và số cửa sổ bị loại.
- [ ] Tích hợp dự báo dưới dạng đề xuất; kiểm chứng fallback và điều kiện an toàn riêng.
- [ ] Bổ sung ảnh/sơ đồ mạch thật, bảng lưu lượng, biểu đồ dữ liệu, video và slide demo.

Không dùng MAE synthetic làm kết quả trên cây thật. Không gộp sửa đổi vào `main`; công việc TV1 tiếp tục trên nhánh riêng.
