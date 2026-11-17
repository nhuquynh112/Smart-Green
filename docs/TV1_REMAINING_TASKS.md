# Việc còn lại của TV1

## Bổ sung 17/11/2026

- Hoàn tất thí nghiệm delta Ridge/HGB/RF với/không ánh sáng cho 30/60 phút; W05 không fit/tune trong thí nghiệm này. Xem [báo cáo delta](DELTA_AI_EVALUATION_2026-11-17.md). Không thay production: chưa thắng Persistence ổn định.
- Rà soát Git: bỏ hai JSON delta trùng, giữ nguồn chuẩn trong artifacts và cập nhật manifest; bảo toàn toàn bộ dữ liệu/model cũ. Thêm ignore file môi trường/cache và giữ byte của các gói checksum khi checkout.
- Sửa thứ tự danh sách phiên khi timestamp có múi giờ khác nhau; regression test đã tái hiện lỗi trước sửa.
- Lượt kiểm thử sau sửa: 176 Python tests và 8 subtests đạt, 8 biến thể PostgreSQL bỏ qua do chưa cấu hình database test riêng; suite Dashboard và firmware native đạt. Đây không phải nghiệm thu bơm thật. Không restart backend, sửa database hoặc gửi lệnh thiết bị trong lượt rà soát này.
- README đã cập nhật; các báo cáo có ngày và bản nháp cũ vẫn giữ làm lịch sử. Các mục nghiệm thu và bảo vệ bên dưới vẫn còn áp dụng.


## Mốc hiện tại — 16/11/2026 (ưu tiên hơn phần lịch sử bên dưới)

Ước lượng **85% phần phát triển**, **khoảng 80% mức sẵn sàng bảo vệ**; đây là đánh giá tiến độ theo bằng chứng, không phải dự báo điểm. Chưa có rubric môn học. Không tính upload/build/test mô phỏng là đã nghiệm thu phần cứng.

### Đã hoàn thành trong source và đánh giá offline

- [x] ESP32 → API → PostgreSQL, dashboard và các guard/chống lặp lệnh có kiểm thử.
- [x] Nhật ký phiên start/finish/save/export, revision và các mốc ánh sáng.
- [x] Đánh giá W01–W05; light ablation 30/60 phút, baseline và giữ nguyên mô hình cũ.
- [x] W05: 927 mẫu, 418/388 cửa sổ; RF có sáng MAE 4,0256/4,2872, Persistence 0,8034/1,4411. Không train W05. W04/W05 cùng chu kỳ tưới.
- [x] Bỏ mật khẩu dự phòng, Chart.js nội bộ, đối soát tưới tay với sự kiện bơm và xử lý reset cũ theo mốc tưới đã biết. 168 Python tests đạt, 7 PostgreSQL variants bỏ qua trong lượt 16/11, 24 Dashboard tests đạt.
- [x] Chuẩn bị gói dữ liệu nghiên cứu W05 đã chọn lọc tại datasets/w05, giữ bản ZIP/database đầy đủ ở local.

### Cần làm theo thứ tự

1. **Nghiệm thu bản cuối**: ghi commit backend/firmware thực chạy; thử đăng nhập, chart khi mất Internet nhưng còn LAN, tạo/lưu/kết thúc/xuất nhật ký và AI available/unavailable đúng điều kiện. Ảnh đăng nhập thành công không xác nhận toàn bộ luồng hoặc phiên bản backend đang chạy.
2. **Đo và ghi bằng chứng phần cứng**: ba lần MANUAL cùng thời lượng, hứng riêng đo ml; STOP/OFF, phao, reset, mất mạng/phục hồi và chống lặp. Kiểm tra motor dừng và nước tự chảy riêng; cần video/log gắn phiên bản. Thử AUTO chỉ sau kiểm tra có giám sát, không mở quyền AI điều khiển.
3. **AI**: ưu tiên thêm một chu kỳ tưới tự nhiên có nhật ký giờ/lượng đo được, giữ vị trí cảm biến; không tưới chỉ để đạt số mẫu. Nếu đổi mô hình/hyperparameter bằng W05 thì W05 thành development, cần giữ phiên tương lai chưa nhìn thấy làm test mới. Không hứa thêm một phiên sẽ làm RF thắng baseline.
4. **Tích hợp TV1/TV2**: demo AI chỉ quan sát với model tương thích device/calibration; nhật ký đã chọn/revision đúng, fallback khi cũ/thiếu/reset phải hoạt động. Không gọi AI observation là đã đạt AI tự điều khiển nếu rubric yêu cầu phần đó.
5. **Báo cáo và bảo vệ**: cập nhật TV1_REPORT_DRAFT cũ bằng W01–W05, bảng MAE/giới hạn, sơ đồ mạch thực tế, hiệu chuẩn, ảnh bố trí, bảng truy vết yêu cầu → test → bằng chứng; làm slide/video demo 5–7 phút.
6. **Tái lập và phục hồi**: kiểm tra clone/môi trường sạch, kiểm thử PostgreSQL riêng, khôi phục backup vào DB thử; không restore lên DB đang dùng để demo. Chốt release commit và lưu video dự phòng.

Chưa xác nhận các mục nghiệm thu live này đạt. Không cần thêm tính năng UI lớn hay chuyển ADC sang lux để hoàn tất phần hiện có. Nếu muốn hướng tới điểm cao, ưu tiên bằng chứng và giải thích trung thực mô hình thất bại, không tăng số mẫu cho đẹp hoặc hứa không còn lỗi.

Báo cáo liên quan: [W05](W05_REVIEW_2026-11-15.md), [bản sửa 16/11](FOLLOWUP_FIXES_2026-11-16.md), [rủi ro đã rà soát](READINESS_REVIEW_2026-11-15.md). Danh sách rủi ro 15/11 là snapshot trước bản sửa, không phải tất cả còn mở.

---

## Mốc lịch sử — 12/11/2026

- Đã sửa luồng điều khiển, trạng thái dashboard và thời điểm tính xung; Python 97 tests + 8 subtests, dashboard 13 tests, native firmware đạt; ESP32 build/upload thành công.
- Đã nạp bản sửa và restart backend lúc khoảng 21:38; telemetry mẫu 2 xác nhận OFF, pump_running=false, clock_ready=true, không lỗi clock/storage. Chưa thử bơm thật trên bản vừa nạp.
- Phiên W01 đã xử lý: 1.062 mẫu trong 8 giờ 50 phút, 528 phút dùng được theo bộ lọc hiện tại. Xem [báo cáo W01](REAL_SESSION_W01_2026-11-11.md). Chưa đủ bằng chứng nhiều chu kỳ độc lập để kết luận AI tốt.

### Buổi test tiếp theo

1. Thử MANUAL cùng thời lượng 3 lần, hứng riêng từng lần và đo ml; quan sát motor dừng và không có nước tự chảy tiếp. Ghi command ID, thời lượng log và quan sát thật. 30–35 ml trước đây chỉ là ước lượng.
2. Xác minh STOP/OFF, phao thiếu nước, OFF sau reset; lưu bằng chứng. STOP qua mạng có độ trễ, ACK không phải cảm biến xác nhận motor.
3. Sau khi cập nhật bản separate-quota-v5: xác nhận ngân sách MANUAL/AUTO riêng, migration giữ sử dụng cũ đến hết cửa sổ. Thử AUTO khô bật/đủ ẩm dừng, hysteresis, khoảng nghỉ và quota. Không xóa NVS để vượt quota.
4. Thử mất Wi-Fi/backend rồi phục hồi, lệnh trùng/hết hạn và reset; đối chiếu DB, ACK, mẫu thiếu và sự kiện, không chỉ nhìn dashboard.

### Để hoàn thành TV1

- [ ] Nghiệm thu phần cứng và điều khiển bằng bảng kết quả trên bản mới; cố định đường ống/cảm biến và đo lưu lượng.
- [x] Sửa quota riêng, timeout, mã yêu cầu bền vững và fence sau STOP; kiểm thử PostgreSQL bằng database tạm riêng.
- [ ] Triển khai backend/firmware mới và nghiệm thu thực tế các sửa đổi 12/11; xem [báo cáo](CODE_REVIEW_2026-11-12.md).
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
