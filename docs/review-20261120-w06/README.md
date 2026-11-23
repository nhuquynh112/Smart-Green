# Tiếp nhận kiểm thử và bản vá chờ hết W06 — 20/11/2026

**Trạng thái cập nhật 21/11/2026: ĐÃ GHÉP VÀO SOURCE sau khi người dùng xác nhận kết thúc phiên thu.**

Đã đối chiếu toàn bộ hash sau áp dụng. Kiểm thử lại trên checkout: **199 Python PASS, 8 SKIP, 8 subtests PASS; Dashboard 30 PASS; AUTO native 36 PASS; firmware native PASS; build esp32dev với cấu hình local SUCCESS**. Bằng chứng: `evidence/applied-*.txt`, trạng thái triển khai: `deployment.json`.

Chưa restart backend, chưa upload firmware, không sửa database vận hành. Cần restart backend và hard-refresh để API/HTML cùng phiên bản; telemetry AUTO bổ sung chỉ xuất hiện sau khi nạp firmware ở bước riêng. Chưa nghiệm thu phần cứng bản mới.

Các phần bên dưới ghi lại quá trình chuẩn bị ngày 20/11. `source-manifest.json` giữ trạng thái lịch sử trước triển khai để truy vết. **Không chạy lại script apply trên source đã áp dụng.**

## Bảo vệ W06

Bản sao làm việc: `/tmp/smart-green-w06-review`. Gói bền vững gồm `changes.patch`, manifest hash, script kiểm tra/áp dụng và bằng chứng tại thư mục này; không phụ thuộc việc giữ `/tmp` để áp dụng.

Không restart backend/Docker, không gọi API thiết bị/phiên thu, không đọc/ghi PostgreSQL vận hành, không mở Serial, không reset/upload ESP32, không đổi cấu hình local. Không sửa các file backend/static hoặc firmware của checkout vận hành trong lượt này. Các sửa AUTO từ lượt trước vẫn giữ nguyên.

Lý do hoãn áp dụng: `backend/static/index.html` được server đọc trực tiếp; ghi đè HTML có thể đổi UI đang dùng dù chưa restart Python. Toàn bộ sửa source nằm trong patch, chỉ tài liệu/bằng chứng được thêm vào repo. Backend launcher không dùng reload, nhưng vẫn chọn cách ly cả backend và UI.

## Nhật ký được tiếp nhận

- `USER_TEST_JOURNAL.md`: giữ nguyên bản người dùng cung cấp, 14 ca kiểm thử thực tế. Đây là báo cáo quan sát của người dùng; trợ lý chưa tự đối chiếu video, log phần cứng hoặc DB của buổi thử.
- `USER_IMPROVEMENT_HANDOFF.md`: giữ nguyên yêu cầu bàn giao, không sửa lịch sử.
- Ca 03: PASS kiểm tra backend, FAIL giao diện; đã có bản vá.
- Ca 08: đất ẩm đồng thời phao thiếu nước, chưa cô lập nguyên nhân không tưới.
- Ca 09: chưa chứng minh chính xác cooldown 5 phút bằng khoảng thời gian nêu trong nhật ký.
- Ca 10: 2 giây còn lại không đủ xung 3 giây là diễn giải phù hợp, chưa chứng minh là nguyên nhân duy nhất.
- STOP/reset theo người dùng đã đạt; chưa đo độ trễ relay, chưa xác minh commit firmware đang chạy.
- 68 lần và 48.134 ms là số tích lũy, không gán toàn bộ cho ngày 20/11.
- Thông tin bổ sung từ ảnh người dùng: **MANUAL 0,5 giây ≈15 mL**, phép đo sơ bộ. Tỷ lệ suy ra ≈30 mL/s chỉ là ứng viên hiệu chuẩn; chưa xác minh độ lặp, không áp dụng cho toàn bộ lịch sử hay suy rằng xung AUTO 3 giây chắc chắn cho 90 mL.

## Sửa lỗi và cải thiện đã chuẩn bị

| Mục | Thay đổi | Giới hạn |
| --- | --- | --- |
| MANUAL nhập 3 giây/backend chỉ cho 1 giây | API dashboard cung cấp `control_limits`; UI dùng min(backend, firmware), hiện giới hạn, đặt max, khóa nút và kiểm tra lại trước gửi; backend kiểm tra độc lập | Không tăng giới hạn. UI mới thiếu cấu hình server thì khóa WATER, vẫn cho STOP |
| Cấu hình backend lỗi | `manual_limits()` kiểm tra giới hạn 1–60000 ms; cấu hình sai khóa WATER và trả lỗi rõ thay vì ValueError/500 | Không dùng fallback rộng hơn để cho tưới |
| AUTO không tưới | Hiển thị điều kiện biết từ mẫu: phao, cảm biến, clock/storage, ngưỡng, cooldown, số lần/ngân sách không đủ xung | Không gọi đây là mã từ chối chính xác của controller; không suy ra “sẵn sàng tưới” khi còn chưa biết chuỗi mẫu khô/guard |
| Cooldown | Hiện khoảng thời gian còn lại theo telemetry, ghi là ước tính | Không đếm ngược từ mẫu cũ/offline; không mặc định 5 phút từ file cấu hình laptop |
| Thông số AUTO | Firmware chỉ bổ sung `auto_low_pct`, `auto_high_pct`, `auto_pulse_ms`, `auto_cooldown_ms`; backend kiểm tra trường tùy chọn | Không đổi thuật toán, relay, ngưỡng, quota hay thời lượng. Firmware cũ vẫn gửi được; UI nói chưa rõ thông số nếu thiếu |
| Offline | Không tuyên bố OFF/đang chạy là trạng thái hiện tại; nhãn soil/tank đánh dấu thông tin cũ | Không suy đoán motor từ Dashboard |
| Đồng bộ | Chỉ có queued_events >0 hiển thị “Đang đồng bộ”; storage/clock fault mới hiện “Cần kiểm tra” | Chưa có timestamp ACK cuối ở telemetry; không tự bịa thời điểm/timeout thất bại |
| Hạn mức | Phân biệt số lần và giây đã dành; giải thích cửa sổ 24 giờ | Không gọi là đặt lại lúc 0h. Thời lượng dành trước không phải tổng thời lượng thực chạy |
| Lịch sử | Dịch Wet, Sensor, Guard sang tiếng Việt | Không sửa sự kiện cũ |
| Số đo đất đổi đột ngột | Gợi ý kiểm tra khi hai mẫu hợp lệ cùng boot/calibration cách ≤90s đổi ≥20 điểm % | Chỉ cảnh báo tham khảo, không lọc/xóa mẫu, không tạo nhãn lỗi hay điều khiển bơm. Không so null thành 0 |
| Lượng nước | Giữ chức năng ước lượng hiện có khi đã cấu hình lưu lượng; lưu phép đo sơ bộ trong nhật ký | Chưa bật quy đổi từ phép đo 15mL đơn lẻ; không xác nhận lưu lượng đã hiệu chuẩn |

Firmware hiện đã lọc trung vị 15 lần đọc ADC (`hardware.h`), controller yêu cầu 3 mẫu khô khác nhau và kiểm tra stale/valid. Không thêm bộ lọc làm thay đổi dữ liệu W06. Cần phép thử đầu dò cố định và đối chiếu ADC/nguồn để kết luận về độ ổn định phần cứng.

## Các file trong patch

- `backend/control_limits.py`: nguồn giới hạn dùng chung.
- `backend/app.py`: trả giới hạn công khai, dùng kiểm tra cấu hình và nhận telemetry AUTO tùy chọn.
- `backend/static/index.html`: UI các mục trên, không sửa logic form phiên thu/AI hoặc biểu đồ dữ liệu.
- `backend/tests/test_control_limits.py`: các ca regression API/giới hạn.
- `backend/tests/dashboard_controls.test.cjs`: fixture API mới và regression UI.
- `firmware/src/main.cpp`: chỉ bổ sung 4 trường quan sát trong publish, không sửa controller.

## Kết quả kiểm thử

| Bộ kiểm tra | Kết quả |
| --- | --- |
| Full Python AI/backend/tools/integration | 198 PASS, 8 SKIP, 8 subtests PASS |
| Kiểm tra giới hạn cuối, sau thêm ca cấu hình sai vẫn cho STOP | 13 PASS (có giao với full suite, không cộng hai số) |
| Dashboard JS | 30 PASS, 0 FAIL |
| AUTO native dùng output giả | 36 PASS, 0 FAIL |
| Firmware native cũ | PASS |
| Build ESP32 trong bản sao, cấu hình mặc định, không upload | SUCCESS |
| Kiểm tra patch áp dụng trên source hiện có | PASS, không áp dụng |

8 SKIP là biến thể PostgreSQL chưa có DB test riêng. Lần chạy đầu bản sao thiếu model demo local dẫn tới 4 FAIL; đã bổ sung bản sao fixture synthetic và chạy lại full suite đạt như trên. Không dùng model demo để kết luận chất lượng AI trên cây thật.

Bằng chứng nằm trong `evidence/`. Kết quả này không chứng minh vật lý relay/phao/nguồn, độ trễ STOP qua mạng hoặc độ chính xác cảm biến. Chưa nghiệm thu UI/API mới trên process đang thu W06.

## Áp dụng sau khi W06 kết thúc

Không thực hiện phần này trong lúc thu. Chốt giờ kết thúc W06, lưu/xuất nhật ký và dữ liệu phiên trước khi thay đổi dịch vụ. Ghi firmware hiện chạy, giữ bản sao cấu hình riêng ngoài Git. Đưa hệ thống về trạng thái kiểm thử với nguồn bơm ngắt.

Tại thư mục repo:

```bash
# Chỉ đối chiếu hash và kiểm tra patch, không thay source:
python3 docs/review-20261120-w06/apply_after_collection.py

# Chỉ sau khi đã kết thúc phiên:
python3 docs/review-20261120-w06/apply_after_collection.py --apply --collection-ended
```

Script từ chối nếu file đã thay đổi kể từ lúc chuẩn bị; không ghi đè sửa đổi mới. Script không restart backend hay upload. Sau áp dụng, chạy lại tests; restart backend có chủ đích sau phiên và hard-refresh Dashboard. Backend và HTML cần triển khai cùng nhau; UI sẽ khóa WATER nếu backend chưa trả giới hạn.

Phần firmware quan sát là bước riêng: build với cấu hình local đã kiểm tra, upload khi không thu và nguồn bơm ngắt, rồi xác nhận telemetry mới có 4 trường. Không cần upload ngay để sửa MANUAL; firmware cũ vẫn được hỗ trợ. Các ngưỡng hiển thị chỉ xuất hiện khi thực sự có telemetry.

Nghiệm thu: backend cap 1000ms/firmware cap 3000ms → UI tối đa 1s; 3s không gửi request; lệnh hợp lệ vẫn ACK; STOP vẫn khả dụng; AUTO đất ẩm + phao đủ nước không tưới; kiểm tra quota/cooldown đúng scope; mất dữ liệu không hiện trạng thái hiện tại giả; form lưu/xuất phiên và dự báo vẫn dùng được.

## Đính chính AI và việc còn lại

Tài liệu bàn giao nói chất lượng AI chỉ có synthetic là chưa cập nhật: repo đã có đánh giá dữ liệu thật W01–W05 và delta 30/60 phút. Xem `../DELTA_AI_EVALUATION_2026-11-17.md`. Không train/chọn model bằng W06 đang thu và không thay model production trong lượt này.

Còn lại, không thể hoàn tất bằng sửa UI:

1. Xác nhận phần cứng cố định: nhiễu/hiệu chuẩn, bảo vệ nguồn/động cơ, chống siphon; không thay dây/phao/cảm biến trong W06.
2. Nghiệm thu độc lập các ca 08/09/10 và đo trễ STOP, ghi phiên bản firmware.
3. Hiệu chuẩn lưu lượng với nhiều lần đo riêng cùng điều kiện; chưa coi 15mL là kết quả chính xác.
4. Hoàn thiện adapter dự báo live delta/light 30/60 và demo AI quan sát; tiếp tục so Persistence, giữ AI không điều khiển bơm. Đây là hạng mục phát triển riêng, chưa nằm trong patch sửa giao diện này.
5. Test PostgreSQL/backup-restore ở DB riêng, clone/môi trường sạch; hoàn thiện báo cáo và video.
6. Bộ lọc lịch sử/ngày, biểu đồ so dự báo-thực tế và bố cục mới là đề xuất phát triển, không phải lỗi đã xác nhận; chưa thêm để tránh mở rộng thay đổi khi phiên thu còn chạy.
