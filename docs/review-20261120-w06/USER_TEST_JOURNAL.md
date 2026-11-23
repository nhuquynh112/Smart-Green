# NHẬT KÝ KIỂM THỬ HỆ THỐNG SMART GARDEN
**Ngày kiểm thử:** 20/11/2026  
**Thiết bị:** ESP32 – Hệ thống giám sát và tưới cây thông minh  
**Hệ thống phần mềm:** FastAPI – PostgreSQL – Dashboard Web  
**Thiết bị phần cứng:** Cảm biến độ ẩm đất, phao báo mức nước, relay, máy bơm DC.

## I. MỤC TIÊU KIỂM THỬ

Kiểm tra khả năng vận hành thực tế của hệ thống Smart Garden, bao gồm:

1. Điều khiển máy bơm ở chế độ MANUAL.
2. Tự động tưới theo ngưỡng độ ẩm đất ở chế độ AUTO.
3. Dừng tưới khi đất đạt độ ẩm cao.
4. Ngăn tưới khi phao báo thiếu nước.
5. Giới hạn thời gian tưới và số lần tưới.
6. Kiểm tra thời gian chờ giữa các lần tưới.
7. Kiểm tra nút STOP khi bơm đang hoạt động.
8. Kiểm tra chế độ an toàn sau khi reset ESP32.
9. Kiểm tra lịch sử hoạt động và đồng bộ dữ liệu.

**Ngưỡng cấu hình được sử dụng để đối chiếu:**
- Ngưỡng đất khô: ≤ 38%.
- Ngưỡng đất đủ ẩm: ≥ 45%.
- Thời gian tưới AUTO quan sát được: khoảng 3 giây/lần.
- Thời gian chờ AUTO được theo dõi: khoảng 5 phút.
- Ngân sách AUTO hiển thị: 20 giây/ngày.
- Giới hạn MANUAL được Backend áp dụng: 1 giây/lệnh.

Lưu ý: Các giá trị trên được tổng hợp từ cấu hình đã trao đổi và Dashboard. Phiên bản firmware đang chạy chưa được đối chiếu lại toàn bộ với mã nguồn sau cùng.

---

## II. NHẬT KÝ KIỂM THỬ CHI TIẾT

### TEST 01 – KẾT NỐI ESP32 VỚI DASHBOARD

**Điều kiện:** ESP32 được cấp nguồn, kết nối Wi-Fi và Backend hoạt động.

**Thao tác:**
- Mở Dashboard tại `http://127.0.0.1:8000`.
- Kiểm tra trạng thái thiết bị.
- Theo dõi dữ liệu cảm biến cập nhật.

**Kết quả quan sát:**
- Dashboard hiển thị Online.
- Dữ liệu độ ẩm đất, nhiệt độ, độ ẩm không khí, ánh sáng và phao nước được cập nhật.
- Các lệnh điều khiển được ESP32 xác nhận.

**Đánh giá: PASS.**

### TEST 02 – CHẾ ĐỘ MANUAL, TƯỚI THEO THỜI GIAN

**Điều kiện:** Thiết bị Online, phao báo đủ nước, chế độ MANUAL.

**Thao tác:**
- Gửi lệnh tưới 0,5 giây.
- Tiếp tục thử các lệnh tưới 1 giây.
- Quan sát máy bơm và lịch sử hoạt động.

**Kết quả quan sát:**

| Thời điểm | Thời gian ghi nhận |
|---|---:|
| 14:07:10 | 504 ms |
| 14:07:49 | 501 ms |
| 14:10:19 | 1.002 ms |
| 14:10:43 | 1.002 ms |
| 14:11:01 | 1.001 ms |
| 14:11:26 | 1.000 ms |
| 14:11:38 | 1.001 ms |

Hệ thống ghi nhận các lần tưới thủ công với thời gian thực tế gần thời gian yêu cầu.

**Đánh giá: PASS.**

### TEST 03 – GIỚI HẠN AN TOÀN THỜI GIAN TƯỚI MANUAL

**Điều kiện:** Chế độ MANUAL, Dashboard cho phép nhập 3 giây.

**Thao tác:** Nhập 3 giây và gửi lệnh tưới.

**Kết quả:**
- Hệ thống từ chối yêu cầu.
- Thông báo: “Thời gian tưới vượt giới hạn an toàn 1000 ms. Yêu cầu bị từ chối.”

**Đánh giá:**
- Kiểm tra giới hạn an toàn: **PASS**.
- Tính nhất quán giao diện: **FAIL – cần sửa**.

**Lỗi cần bàn giao:** Dashboard cho phép nhập thời gian vượt giới hạn Backend chấp nhận.

### TEST 04 – AUTO KHI ĐẤT KHÔ VÀ PHAO ĐỦ NƯỚC

**Điều kiện:**
- Chế độ AUTO.
- Độ ẩm đất thấp hơn ngưỡng 38%.
- Phao báo đủ nước.

**Thao tác:**
- Chuyển hệ thống sang AUTO.
- Giữ điều kiện đất khô.
- Theo dõi thời gian chờ và lịch sử tưới.

**Kết quả quan sát:**
- 13:17:38: AUTO chạy khoảng 3,002 giây.
- 13:27:42: AUTO chạy khoảng 3,001 giây.
- 13:35:07: AUTO chạy khoảng 3,001 giây.
- 13:57:09: AUTO chạy khoảng 3,002 giây.

Em xác nhận các lần thử được thực hiện với máy bơm có cấp nguồn và bơm hoạt động thực tế.

**Đánh giá: PASS.**

### TEST 05 – AUTO DỪNG KHI ĐẤT ĐẠT NGƯỠNG CAO

**Điều kiện:** AUTO đang hoạt động, độ ẩm đất tăng đến ngưỡng dừng.

**Kết quả quan sát:**
- 12:59:10: Có sự kiện AUTO, thời gian khoảng 1.515 ms.
- Lý do dừng được ghi nhận: `Wet`.

**Đánh giá: PASS đối với logic ghi nhận và dừng theo ngưỡng.**

Chưa dùng kết quả này để khẳng định cảm biến phản ánh chính xác độ ẩm đất thực tế, vì các giá trị cảm biến từng thay đổi mạnh trong quá trình thử.

### TEST 06 – MANUAL KHI PHAO BÁO HẾT NƯỚC

**Điều kiện:** Phao báo thiếu nước.

**Thao tác:** Chuyển sang MANUAL và thử gửi lệnh tưới.

**Kết quả:**
- Dashboard hiển thị cảnh báo hết nước.
- Hệ thống khóa yêu cầu tưới.
- Em xác nhận máy bơm không hoạt động.

**Đánh giá: PASS.**

### TEST 07 – AUTO KHI PHAO BÁO HẾT NƯỚC

**Điều kiện:**
- Chế độ AUTO.
- Đất có độ ẩm thấp, đủ điều kiện yêu cầu tưới.
- Phao báo thiếu nước.

**Thao tác:** Duy trì điều kiện và quan sát hệ thống.

**Kết quả:**
- Hệ thống không tiếp tục tưới khi phao báo thiếu nước.
- Lịch sử lúc 13:22:41 ghi nhận một lần AUTO dừng với lý do thiếu nước, thời gian khoảng 1.326 ms.
- Các lần theo dõi tiếp theo không phát sinh tưới mới khi điều kiện thiếu nước vẫn được duy trì.

**Đánh giá: PASS.**

### TEST 08 – AUTO KHI ĐẤT ĐỦ ẨM

**Điều kiện:**
- Chế độ AUTO.
- Phao báo thiếu nước trong lần thử được ghi nhận.
- Độ ẩm đất khoảng 53,39–56,53%, cao hơn ngưỡng 45%.

**Thao tác:** Duy trì trạng thái AUTO và quan sát lịch sử.

**Kết quả:** Không ghi nhận lần tưới mới trong khoảng theo dõi.

**Đánh giá: PASS có điều kiện.**

**Giới hạn bằng chứng:** Vì phao đồng thời báo thiếu nước, chưa thể khẳng định riêng điều kiện đất đủ ẩm là nguyên nhân ngăn tưới. Cần thử độc lập với phao đủ nước nếu muốn xác nhận đầy đủ ca này.

### TEST 09 – THỜI GIAN CHỜ GIỮA CÁC LẦN TƯỚI AUTO

**Điều kiện:**
- AUTO.
- Đất khô.
- Phao đủ nước.

**Thao tác:** Theo dõi các lần kích hoạt AUTO và thời điểm xuất hiện lần tưới tiếp theo.

**Kết quả:**
- 13:35:07: Có một lần AUTO.
- 13:57:09: Có lần AUTO tiếp theo.
- Trong các khoảng theo dõi ngắn, hệ thống không tưới liên tục.

**Đánh giá: PASS có điều kiện.**

Các ảnh chứng minh hệ thống không tưới liên tục, nhưng chưa đủ để xác nhận chính xác thời gian cooldown thực tế là 5 phút. Cần đối chiếu firmware hoặc nhật ký trạng thái cooldown.

### TEST 10 – GIỚI HẠN NGÂN SÁCH TƯỚI AUTO

**Điều kiện:**
- Ngân sách AUTO hiển thị 20 giây.
- Sau lần tưới lúc 13:57, Dashboard hiển thị còn khoảng 2 giây.
- Mỗi lần tưới AUTO thông thường cần khoảng 3 giây.

**Thao tác:**
- Tiếp tục giữ AUTO.
- Đất khô và phao đủ nước.
- Theo dõi đến 14:04.

**Kết quả:**
- Không xuất hiện thêm sự kiện AUTO.
- Tổng số lần AUTO giữ nguyên ở 7 lần.
- Ngân sách đã dành giữ nguyên khoảng 18/20 giây.

**Đánh giá: PASS theo kết quả quan sát.**

**Giới hạn bằng chứng:** Việc không tưới phù hợp với cơ chế chặn khi ngân sách còn ít hơn thời gian xung tưới. Tuy nhiên, chưa có nhật ký mã lỗi từ firmware chứng minh ngân sách là điều kiện chặn duy nhất.

### TEST 11 – RESET ESP32 VÀ TRẠNG THÁI AN TOÀN

**Điều kiện:** ESP32 đang ở chế độ AUTO.

**Thao tác:** Nhấn nút RESET trực tiếp trên ESP32.

**Kết quả:**
- Dashboard sau reset hiển thị OFF.
- Em xác nhận hệ thống tự chuyển về OFF sau khi reset.

**Đánh giá: PASS.**

### TEST 12 – STOP KHI BƠM ĐANG CHẠY

**Điều kiện:** Máy bơm đang hoạt động.

**Thao tác:** Nhấn nút STOP trên Dashboard.

**Kết quả em xác nhận:**
- Máy bơm dừng sau khi nhấn STOP.
- Hệ thống chuyển sang OFF.

**Đánh giá: PASS theo quan sát thực tế.**

**Giới hạn bằng chứng:** Chưa ghi nhận độ trễ từ lúc nhấn STOP đến lúc relay ngắt. Chưa đối chiếu riêng sự kiện STOP trong lịch sử lệnh của lần thử này.

### TEST 13 – GHI NHẬN LỊCH SỬ CHẠY BƠM

**Thao tác:** Kiểm tra bảng lịch sử chạy bơm sau các lần MANUAL và AUTO.

**Kết quả lúc 14:11:**

| Chỉ tiêu | Giá trị |
|---|---:|
| Tổng số lần chạy | 68 |
| Số lần MANUAL | 61 |
| Số lần AUTO | 7 |
| Tổng thời gian ghi nhận | 48.134 ms |
| Ngân sách AUTO đã dành | 18/20 giây |

Lịch sử hiển thị thời điểm, nguồn kích hoạt, lý do và thời lượng.

**Đánh giá: PASS.**

**Lưu ý:** Đây là số liệu tích lũy trên Dashboard, không phải toàn bộ 68 lần đều phát sinh trong ngày kiểm thử.

### TEST 14 – ĐỒNG BỘ DỮ LIỆU ESP32 VỚI BACKEND

**Hiện tượng ban đầu:** Dashboard báo “Cần kiểm tra – Còn 1 sự kiện chờ gửi”.

**Thao tác:** Tiếp tục theo dõi và mở mục Chi tiết thiết bị.

**Kết quả lúc 14:12:**
- Trạng thái: Đã đồng bộ.
- Sự kiện chờ gửi (`queued_events`): 0.
- Không phát hiện lỗi lưu trữ.
- Đồng hồ hệ thống đã đồng bộ.
- Không phát hiện lỗi đồng hồ.

**Đánh giá: PASS.**

Cảnh báo trước đó đã tự hết sau khi đồng bộ. Không xác định đây là lỗi phần mềm.

---

## III. TỔNG HỢP KẾT QUẢ

| STT | Ca kiểm thử | Kết quả |
|---|---|---|
| 01 | Kết nối ESP32 – Dashboard | PASS |
| 02 | MANUAL 0,5–1 giây | PASS |
| 03 | Giới hạn thời gian MANUAL | PASS logic / FAIL giao diện |
| 04 | AUTO khi đất khô, đủ nước | PASS |
| 05 | Dừng AUTO khi đất đạt ngưỡng cao | PASS logic |
| 06 | MANUAL khi phao hết nước | PASS |
| 07 | AUTO khi phao hết nước | PASS |
| 08 | AUTO khi đất đủ ẩm | PASS có điều kiện |
| 09 | Thời gian chờ AUTO | PASS có điều kiện |
| 10 | Giới hạn ngân sách AUTO | PASS theo quan sát |
| 11 | Reset ESP32 → OFF | PASS |
| 12 | STOP khi đang bơm → OFF | PASS |
| 13 | Lịch sử chạy bơm | PASS |
| 14 | Đồng bộ dữ liệu | PASS |

**Tổng số ca:** 14.

**Kết quả:** Các chức năng cốt lõi đã được kiểm thử và cho kết quả tích cực. Một số ca vẫn cần bằng chứng độc lập hoặc đối chiếu firmware để khẳng định đầy đủ.

---

## IV. LỖI VÀ HẠN CHẾ CẦN BÀN GIAO

### Lỗi 01 – Giới hạn thời gian MANUAL không đồng nhất

**Hiện trạng:** Dashboard cho nhập 3 giây nhưng Backend từ chối vì giới hạn an toàn là 1.000 ms.

**Yêu cầu:**
- Đồng bộ giới hạn thời gian giữa Firmware, Backend và Dashboard.
- Giới hạn giá trị có thể nhập trên giao diện.
- Hiển thị rõ thời gian tưới tối đa.
- Thông báo lỗi dễ hiểu.
- Không tự ý nâng giới hạn an toàn.

**Trạng thái: CHƯA SỬA.**

### Hạn chế 02 – Chưa xác nhận độc lập một số điều kiện AUTO

Cần bổ sung bằng chứng nếu yêu cầu báo cáo có độ chặt chẽ cao:
- Đất đủ ẩm, phao vẫn đủ nước, AUTO không tưới.
- Xác nhận thời gian cooldown thực tế từ firmware.
- Xác nhận nguyên nhân chặn tưới khi ngân sách không đủ.
- Đo thời gian phản hồi STOP.

### Hạn chế 03 – Phần cứng và cảm biến

- Chưa hoàn thiện bảo vệ điện cho động cơ bằng diode chống điện áp ngược và tụ lọc nguồn.
- Cần kiểm tra nguy cơ nước tiếp tục chảy do hiệu ứng siphon sau khi tắt bơm.
- Cảm biến độ ẩm từng có các bước nhảy lớn giữa 0% và trên 50%; cần kiểm tra hiệu chuẩn và độ ổn định.
- Chưa hiệu chuẩn lưu lượng nước thực tế, nên Dashboard chưa thể quy đổi chính xác thời gian tưới sang ml.

---

## V. KẾT LUẬN KIỂM THỬ NGÀY 20/11/2026

Hệ thống Smart Garden đã thể hiện khả năng điều khiển tưới thủ công và tự động theo các điều kiện cảm biến. Các chức năng an toàn quan trọng như khóa tưới khi thiếu nước, giới hạn thời gian tưới, giới hạn ngân sách, STOP và chuyển về OFF sau reset đã có kết quả thử nghiệm tích cực.

Dashboard đã ghi nhận lịch sử tưới và đồng bộ dữ liệu từ ESP32 với Backend.

Tuy nhiên, kết quả kiểm thử hiện tại chưa đủ để tuyên bố toàn bộ hệ thống đã được xác minh hoàn toàn hoặc sẵn sàng vận hành không giám sát trong thời gian dài. Cần hoàn thiện bảo vệ phần cứng, khắc phục lỗi giao diện MANUAL và xác nhận độc lập các điều kiện AUTO còn thiếu bằng chứng.

**Định hướng tiếp theo:**
1. Chốt nhật ký kiểm thử phần cứng và điều khiển.
2. Bàn giao lỗi MANUAL để sửa.
3. Hoàn thiện mô hình dự báo AI bằng dữ liệu thực tế.
4. Tích hợp kết quả AI vào Dashboard; đánh giá riêng trước khi cho phép AI tác động đến điều khiển bơm.
5. Cải thiện giao diện, kiểm tra cơ sở dữ liệu và chuẩn bị demo đồ án.

**Trạng thái kết thúc buổi kiểm thử:** STOP/OFF; cần ngắt nguồn riêng của bơm khi không tiếp tục thử nghiệm.