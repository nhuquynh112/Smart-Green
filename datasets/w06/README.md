# W06 — kiểm tra PostgreSQL ngày 21/11/2026

## A. Trạng thái: CẦN XÁC MINH để dùng cho AI; lưu/đóng phiên PASS

Đọc PostgreSQL trực tiếp bằng transaction REPEATABLE READ, READ ONLY; không khởi tạo backend/migrate hoặc cập nhật DB. Tên phiên `W-20261120-075322-1580`, khóa DB thực `15802fb9a287239d0378191115df91b5`. Revision 4, active=0, document end đã lưu. Revision cuối khớp document hiện tại. history_complete=true thực sự lưu trong DB, nhưng last_watered_at_before_start=null. Giữ nguyên nhật ký, không tự xác nhận lại.

## B. Dữ liệu

- 1.237 bản ghi real garden-01, cùng soil-2511-979.
- Phiên: 20/11/2026 14:53:22 → 21/11/2026 01:11:59 Việt Nam: 10h18m37s.
- Mẫu đo: 14:53:40 → 01:11:42: 10h18m02s.
- Nhận ở server: 14:53:43.127053 → 01:11:44.593890: 10h18m01.466837s.
- Nhịp đo 29–31s, trung vị 30s. Nhịp nhận 21.398–44.308s, trung vị 29.988s; trễ nhận trung vị 2.547s, tối đa 16.274s.
- Một boot, sequence liên tục, không trùng khóa/mốc đo, không timestamp đi ngược/thiếu, không gap >90s. Không chứng minh được mọi gián đoạn Wi-Fi ngắn chỉ bằng telemetry.
- Đất hợp lệ 37.663–51.762%; nhiệt 31.9–33.8°C; RH 52.1–69.7%; ánh sáng 1716–3867 ADC, đủ 100%, không bão hòa 4095. ADC không phải lux.

## C. Bất thường và đối chiếu

6 mẫu soil_raw=0, soil_pct=null, soil_valid=false lúc **23:55:12–23:57:42 ngày 20/11**; không nội suy hoặc xóa. Cần kiểm tra đầu nối/nguồn/đầu dò trước phiên tiếp; dữ liệu không đủ xác định nguyên nhân. Không có biến động liên tiếp ≥20 điểm % trong các giá trị đất hợp lệ.

Toàn bộ mẫu OFF/pump_running=false, queued_events=0, clock_fault=false, storage_fault=false. Không lệnh điều khiển hoặc watering_event giao khoảng phiên. telemetry_overwrites=13 không tăng: số tích lũy, không quy kết 13 mẫu mất trong W06. Không thấy reset hoặc đổi calibration trong phiên.

Sự kiện bơm cuối trước phiên: #68, 20/11 14:11:38–14:11:39.001. Người dùng xác nhận kiểm thử này **không tưới cây**. Không dùng sự kiện đó làm giờ tưới chậu. Nhật ký trống không chứng minh không tưới tay. Chưa có giờ tưới chậu gần nhất và xác nhận đầy đủ lịch sử từ lần tưới đó đến hết W06.

## D. Cửa sổ

Pipeline hiện có build_ai_dataset.build → light_supervised, timestamp thiết bị, chỉ phút đóng, giữ nguyên journal DB:

| Horizon | Cửa sổ AI hợp lệ có/không ánh sáng | Ứng viên chỉ xét cảm biến |
|---|---:|---:|
| 30 phút | 0 / 0 | 524 |
| 60 phút | 0 / 0 | 466 |

618 phút đóng được xét; thiếu giờ tưới trước phiên khiến toàn bộ bị loại `unknown_previous_watering`. Ứng viên cảm biến chỉ đếm đoạn đầy đủ 16 phút lịch sử và toàn bộ horizon, loại phút biên/đất lỗi; **không phải cửa sổ được phép train/test**, chưa chứng minh lịch sử tưới. Không tạo giờ tưới giả để mở khóa pipeline. light-minutes.csv phản ánh đúng kết quả bị khóa hiện tại.

## E. Giá trị cho AI

Giữ W06 làm dữ liệu thực chờ hoàn thiện metadata. Chưa đủ điều kiện train/test theo bộ đặc trưng hiện tại; không train hoặc đánh giá mô hình trong lượt này. Sau xác nhận giờ tưới và lịch sử, chạy lại pipeline, loại cửa sổ đi qua phút cảm biến lỗi, không xóa bản gốc.

So trực tiếp nguồn W01–W05, W06 có đất 37.663–51.762%, cao hơn cực đại các phiên cũ (W01 26.110%, W04 23.042%, W05 11.292%). Nhiệt tối đa 33.8°C cao hơn các phiên cũ, RH thấp hơn; bổ sung giai đoạn chiều–đêm và ADC không bão hòa. Đây là thay đổi phân bố đáng kể, không tự kết luận do chu kỳ tưới mới hay đất thực ẩm hơn: cần xác nhận vị trí/tiếp xúc đầu dò và lịch sử từ W05. Cùng mã calibration không chứng minh cùng điều kiện lắp đặt.

## F–G. Sẵn sàng W07 và kế hoạch W07–W10

Không có session active trong snapshot DB. W06 đã kết thúc, nguồn tạo phiên dùng UUID, optimistic revision và unique active/device; không ghi đè telemetry cũ. Code chưa ngăn mọi khoảng thời gian chồng nhau khi sửa tay ngày giờ, vì vậy dùng chức năng bắt đầu/kết thúc thực tế, không sửa thời gian chồng phiên cũ.

Mẫu cuối toàn thiết bị khi kiểm tra vẫn là 21/11 01:12:14.649365, OFF, calibration soil-2511-979. **Chưa xác nhận thiết bị đang online bằng dữ liệu mới**, nên chưa kết luận bắt đầu W07 ngay.

Trước W07: kiểm tra đầu dò/nguồn và đọc ổn định vài phút; online và timestamp hiện tại; calibration đúng; xác nhận giờ tưới cây gần nhất, lịch sử tưới tay và thay đổi vị trí từ W05. Giữ cấu hình/firmware, AUTO OFF; không thử bơm trong phiên nghiên cứu. Không thay đổi calibration chỉ để số đẹp. Nếu cần hiệu chuẩn mới thì tạo mã mới và tách nhóm dữ liệu.

- W07: 8–12h ban ngày, vị trí cố định; ghi đúng lần tưới gần nhất. Không tưới chỉ để tăng mẫu.
- W08: 8–12h chiều–đêm, ghi nguồn sáng thực tế; nếu cùng chu kỳ W07 thì cùng nhóm chia train/test.
- W09: ghi 30–60 phút trước lần tưới tự nhiên cần thiết, giờ bắt đầu/kết thúc/lượng đo thực tế, tiếp tục 8–12h sau tưới. Cửa sổ đi qua tưới bị loại theo bài toán hiện tại.
- W10: ưu tiên chu kỳ tưới khác làm kiểm thử độc lập; chốt mô hình/siêu tham số từ nhóm phát triển trước khi xem kết quả W10. Nếu vẫn cùng chu kỳ W09, không gọi là chu kỳ kiểm thử mới.

Mỗi phiên: lưu mốc reset/mất điện/di chuyển/che sáng/tưới tay ngay lúc xảy ra, chốt giờ cuối, đối soát rồi export. Không tự động đánh dấu đối soát hoặc kích hoạt AI điều khiển.

## Tệp và bảo toàn

`database-rows.jsonl`, session-record/revisions, journal, watering-events, commands là snapshot đọc từ DB. watering-events gồm cả lịch sử trước phiên để đối chiếu; không gán tất cả cho W06. `telemetry.jsonl` chuẩn hóa tên measured_at→timestamp và pump_running→pump_on, không sửa số đo. `quality.json` có thống kê chi tiết, `manifest.json` có SHA256. Bản sao ZIP nằm ở artifacts/w06-backup-20261121.zip. Chưa push; snapshot đầy đủ cần rà soát thông tin vận hành trước công bố.

## Xác nhận bổ sung ngày 21/11/2026

Người dùng xác nhận **không tưới cây trong W06 vì độ ẩm vẫn còn cao**. Kết hợp với không có sự kiện bơm trong phiên, đã bổ sung bằng chứng lịch sử trong phiên. Giờ tưới cây gần nhất trước W06 vẫn chưa rõ; số cửa sổ AI hiện tại chưa thay đổi. `journal.json` và snapshot DB giữ nguyên; xác nhận bổ sung lưu tại `user-confirmations.json`. Không sửa phiên W07 đang thu.

## Gói công bố Git — 23/11/2026

Git chỉ chứa telemetry chuẩn hóa, nhật ký, metadata phiên, xác nhận người dùng và kết quả chất lượng. Snapshot database đầy đủ/lịch sử lệnh và sự kiện ngoài phiên giữ local, được loại khỏi Git bằng .gitignore; các ZIP sao lưu ở artifacts vẫn giữ nguyên. manifest.json kiểm tra các file công bố; manifest-local.json và ZIP giữ checksum snapshot trước công bố. Chưa đủ metadata để train/test theo pipeline hiện tại.
