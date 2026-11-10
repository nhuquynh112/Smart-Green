# Việc còn lại của TV1

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
