# AUTO: bản sửa, nghiệm thu và phần AI còn lại — 20/11/2026

Bản này cập nhật kết luận của `AUTO_LOGIC_AUDIT_2026-11-20.md`. Audit cũ và log trong `auto-audit-20261120` là bằng chứng trước sửa; mã và log sau sửa nằm trong `auto-fixes-20261120`. Chưa upload firmware, restart backend, mở Serial, gửi lệnh thiết bị hoặc thay đổi database vận hành. Không sửa Dashboard, dữ liệu W01–W05, mô hình hay cấu hình ngưỡng/hạn mức.

## Những gì đã sửa

1. **ACK lỗi không chặn nhận STOP/OFF**: thêm `command_delivery.h` và hai queue riêng cho lệnh/ACK an toàn. Khi ACK thường lỗi, worker vẫn hỏi lệnh; chỉ STOP/OFF được qua, các lệnh bật tiếp tục bị khóa. Main xử lý lane an toàn trước và không phụ thuộc chỗ trống của queue ACK thường. ACK thường và ACK an toàn đều được giữ để retry, không ghi đè/mất ACK để giải phóng queue. Nếu ACK STOP còn lỗi thì khóa nhận lệnh mới trong khi thiết bị đã OFF. Không tự bỏ ACK 404/500.
2. **Khởi động/reset trở về OFF**: runtime và bridge mô phỏng gọi `disarmAfterBoot()` trước khi chạy vòng điều khiển. Giữ watermark, ngân sách và nhật ký; sự kiện đang chạy chuyển Reboot với thời lượng vật lý không xác định. Không tự bật lại chỉ vì NVS lưu AUTO. Ghi trạng thái OFF thất bại thì khóa lỗi, không cho chạy. Muốn chạy lại cần lệnh chọn chế độ hợp lệ mới. Điều này không hủy mọi lệnh chưa thực thi còn hợp lệ trên server; trước nghiệm thu phải STOP và đối soát hàng đợi, không để yêu cầu AUTO đang chờ từ trước.
3. **STOP/OFF đến muộn vẫn chặn lệnh bật cũ**: lưu watermark tăng đơn điệu kể cả khi STOP hết hạn/clock chưa sẵn sàng. Lệnh bật cũ trong queue hoặc gửi lại sau reboot không được tái kích hoạt AUTO. Lệnh STOP trùng vẫn tắt an toàn.

STOP mạng vẫn phụ thuộc Wi-Fi/backend và timeout HTTP; không phải nút ngắt điện tức thời. Mất toàn bộ mạng vẫn không nhận được STOP web. AUTO đang được chọn vẫn hoạt động theo cảm biến/guard/quota cục bộ khi mất mạng; bản này không đổi chính sách đó. Không coi đèn Online hoặc ACK là cảm biến xác nhận motor.

## Kiểm thử và giới hạn

- Native AUTO: 36 PASS, 0 FAIL. A30 đổi sang kiểm tra runtime disarm; A33–A36 kiểm tra scheduling ACK lỗi, hàng rào STOP cũ, lỗi lưu boot và phân loại lệnh ưu tiên.
- Native controller/safety/runtime/profile/telemetry: PASS.
- Bộ Python cuối: **186 PASS, 8 SKIP, 8 subtests PASS**; xem `auto-fixes-20261120/pytest-results.txt` và JUnit; 8 biến thể PostgreSQL cần DB test riêng nên SKIP. Không chạy trên DB thật.
- Dashboard: suite hiện có PASS; không sửa UI.
- Build `esp32dev`: SUCCESS (chỉ compile, không upload).
- Host tests chạy shared controller và shared delivery policy; integration chạy bridge C++ với backend và DB tạm. Chúng chưa giả lập toàn bộ FreeRTOS/HTTPClient/NVS thật. Queue đã compile trên ESP32; độ trễ Wi-Fi, lịch task, relay, phao, sụt nguồn và nước tự chảy vẫn phải nghiệm thu phần cứng.

Chạy lại mô phỏng, không cần USB:

```bash
cd /home/ad/Desktop/Smart-Green
bash tools/test_auto_audit.sh
bash tools/test_firmware.sh
PYTHONPATH=ai OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv-ai/bin/python -m pytest -q ai/tests backend/tests tools/tests integration
node --test backend/tests/dashboard_controls.test.cjs
```

## Buổi nghiệm thu AUTO có giám sát

**Chỉ áp dụng sau khi nạp đúng bản sửa; hiện ESP32 chưa được cập nhật.** Thực hiện sau phiên thu, ghi commit/firmware thực chạy. Bắt đầu với nguồn bơm ngắt, giữ ESP32 hoạt động để kiểm tra trạng thái. Không nối tắt phao, xóa NVS hoặc tăng hạn mức để ép test. Đấu dây/chuyển dây khi đã ngắt nguồn.

| Bước | Thực hiện | Kết quả mong đợi |
| --- | --- | --- |
| 1 | STOP, kiểm tra hàng đợi không còn lệnh bật chờ; reset ESP32 | OFF, đầu ra không bật; quota và nhật ký còn nguyên |
| 2 | Kiểm tra clock, soil valid, phao đủ nước, quota còn; chọn AUTO | AUTO được ACK; không suy ra bơm phải bật ngay |
| 3 | Dùng điều kiện đất khô đã xác minh; chờ đủ mẫu và cooldown | Theo cấu hình local hiện tại: ≤30, ít nhất 3 mẫu đất khác nhau; nghỉ 10 phút từ boot/lần dừng; đủ guard thì một xung tối đa 1 giây |
| 4 | Xác minh đầu ra rồi thử một xung thật vào bình hứng, có người giám sát | Motor tự dừng; nước không tự chảy liên tục; log source RULE, lý do/thời lượng phù hợp |
| 5 | Đưa cảm biến sang điều kiện ẩm kiểm chứng trên mẫu riêng, không xáo trộn phiên nghiên cứu | ≥45 không bật/dừng xung; vùng 30–45 không đủ điều kiện khởi động mới |
| 6 | Thử phao thiếu nước; sau đó STOP/OFF | Thiếu nước không khởi động/dừng tại thiết bị; STOP/OFF tắt và không tự chạy lại |
| 7 | Reset khi AUTO nhưng chưa cấp nguồn bơm | Trở về OFF, không tự phục hồi AUTO sau thời gian nghỉ |
| 8 | Thử mất LAN/backend với nguồn bơm ngắt; phục hồi | Không kỳ vọng STOP web khi mất mạng; guard/quota local còn tác dụng, sự kiện retry không nhân bản |

Giới hạn số lần/thời gian và cảm biến NaN/stale đã kiểm tra tự động; không cần bơm thật 20 lần hay gửi telemetry giả vào database nghiên cứu. Với test ACK 500/404, dùng môi trường test/fault injection riêng, không sửa API vận hành.

Ghi mỗi ca: phiên bản, thời gian, command/event ID, trạng thái trước/sau, quan sát motor/nước, ảnh hoặc video, PASS/FAIL. Nếu nước tiếp tục chảy sau motor dừng, kiểm tra bố trí ống/chênh cao; sửa software không giải quyết dòng chảy tự nhiên. Nếu đầu ra không dừng như dự kiến thì ngắt nguồn bơm và dừng nghiệm thu.

## AI thực tế đang tích hợp tới đâu?

**Có đường tích hợp dự báo, chưa có AI tự điều khiển.**

- `backend/app.py`: POST `/api/v1/web/devices/{device_id}/predict` cho nút dự báo Dashboard, GET API dự báo, lưu kết quả vào `ai_predictions`, trả lịch sử dự báo cho Dashboard.
- `backend/ai_service.py`: tổng hợp phút đã hoàn tất, kiểm tra cảm biến và lịch sử tưới. Dữ liệu thật yêu cầu phiên nhật ký đã lưu, revision và boot/thời điểm đối soát đúng.
- `ai/smart_green_ai/inference.py`: kiểm tra version/device/calibration/origin/time_basis và độ mới trước dự báo; trả `can_trigger_pump=false`.
- AUTO trên ESP32 là **luật ngưỡng**, không gọi mô hình Python. Cờ quyền AI điều khiển không được bật trong bản sửa này.
- Light/delta Ridge/HGB/RF 30/60 phút đã có thí nghiệm offline; adapter live hiện dùng schema/bundle cũ, chưa nối các bundle delta/light vào đường dự báo live. Backend hiện nạp một bundle/horizon. Chưa thể gọi đây là tính năng live đồng thời cả 30 và 60 phút.
- Mặc định source dùng `artifacts/offline-demo-v2/model/candidate.joblib` nếu không có `SG_AI_MODEL_PATH`. Đây không xác nhận model đang nạp trong process vận hành. Bundle synthetic không được dùng cho dữ liệu real. Cần kiểm tra cấu hình model hợp lệ khi làm demo.

Bằng chứng W05 trong báo cáo delta: Persistence MAE 0,8034/1,4411 (30/60 phút); RF delta không sáng 0,8794/1,4529; HGB delta có sáng 1,6066/1,4223. Không có phương án mới thắng baseline ổn định cả hai horizon. Vì vậy chưa có căn cứ tự thay production hay cấp quyền bơm cho AI. Không gọi Persistence là mô hình học máy đã chứng minh cải thiện.

## Những công việc còn lại để chốt đồ án

1. **Nghiệm thu điều khiển bản sửa**: nạp firmware đúng phiên bản, làm bảng trên với giám sát; kiểm tra phao, relay, reset và mất mạng thực tế. Kiểm tra thêm lỗi ACK trên môi trường mạng thử riêng. Không tính mô phỏng là đã nghiệm thu phần cứng.
2. **Hoàn thiện demo AI quan sát**: xác nhận bundle real tương thích với garden/calibration; kết nối adapter delta/light và lựa chọn horizon 30/60 nếu cần trình diễn các thí nghiệm mới. Giữ mô hình cũ, model thử nghiệm tách biệt; hiển thị baseline, thời điểm và điều kiện “không tưới thêm”. Thử available/unavailable với dữ liệu thật đủ 16 phút hoàn tất, nhật ký hợp lệ, mẫu cũ/thiếu/reset/sai calibration. Chưa triển khai adapter mới trong lượt sửa AUTO này.
3. **Bằng chứng AI**: dùng chu kỳ tưới tương lai chưa dùng chọn model để đánh giá, chỉ tưới theo nhu cầu cây; giữ W01–W05 và báo cáo cũ. Nếu không cải thiện Persistence thì báo cáo trung thực giới hạn; không cần ép mô hình phức tạp để đạt điểm.
4. **Tích hợp và dữ liệu**: test PostgreSQL trên DB riêng, clone/môi trường sạch, backup/restore vào DB test; nghiệm thu đăng nhập, phiên thu/export và dự báo toàn luồng.
5. **Hồ sơ bảo vệ**: cập nhật báo cáo với W01–W05 và delta; sơ đồ mạch thật, bảng hiệu chuẩn/lưu lượng, bảng yêu cầu→test→bằng chứng, sơ đồ phân biệt AUTO luật và AI dự báo; slide/video 5–7 phút, hướng dẫn chạy lại và release commit.

Không có cơ sở hứa điểm 9,5 hay “không còn lỗi”. Phần cần ưu tiên là demo AI live đúng nghĩa và bằng chứng nghiệm thu, không phải thêm Dashboard mới hoặc tăng số mẫu đơn thuần.
