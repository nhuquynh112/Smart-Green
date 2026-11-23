# VI. DANH SÁCH CHỈNH SỬA, CẢI TIẾN VÀ PHÁT TRIỂN HỆ THỐNG SMART GARDEN

**Ngày lập:** 20/11/2026  
**Dự án:** Smart Garden – Hệ thống giám sát và tưới cây thông minh ứng dụng IoT và AI  
**Nền tảng:** ESP32 – FastAPI – PostgreSQL – Dashboard Web – Machine Learning

## 6.1. TỔNG QUAN TÌNH TRẠNG HỆ THỐNG

Sau quá trình kiểm thử thực tế, hệ thống Smart Garden đã vận hành được các chức năng điều khiển cơ bản.

**Các chức năng đã hoạt động:**
- ESP32 kết nối và đồng bộ dữ liệu với Backend.
- Dashboard hiển thị dữ liệu cảm biến theo thời gian.
- Chế độ MANUAL điều khiển máy bơm.
- Chế độ AUTO tự động tưới theo ngưỡng độ ẩm đất.
- Ngăn tưới khi phao báo thiếu nước.
- Dừng tưới khi đất đạt ngưỡng độ ẩm cao.
- Giới hạn thời gian và ngân sách tưới.
- Nút STOP dừng máy bơm và chuyển hệ thống về OFF.
- ESP32 chuyển về OFF sau khi reset.
- Lưu lịch sử hoạt động của máy bơm.
- Đồng bộ dữ liệu giữa thiết bị và Backend.

**Tình trạng AI hiện tại:**
- Đã có API phục vụ dự báo.
- Đã có giao diện hiển thị kết quả dự báo.
- Đã có chức năng lưu kết quả dự báo.
- Đã có các mô hình dự báo và cơ chế đánh giá.
- AUTO hiện vẫn điều khiển theo ngưỡng.
- Kết quả AI chưa trực tiếp tham gia quyết định tưới.
- Chất lượng mô hình trên dữ liệu thực tế chưa được xác minh đầy đủ.

**Mục tiêu giai đoạn tiếp theo:** Hoàn thiện tính ổn định, sửa lỗi giao diện, nâng cao chất lượng AI và chuẩn bị hệ thống để trình diễn đồ án.

---

## 6.2. DANH SÁCH LỖI VÀ VẤN ĐỀ CẦN CHỈNH SỬA

### 6.2.1. LỖI 01 – GIỚI HẠN THỜI GIAN TƯỚI MANUAL KHÔNG ĐỒNG NHẤT

**Mức độ ưu tiên: P1 – Cao**

**Hiện trạng:**

Trong quá trình kiểm thử lúc 14:09 ngày 20/11/2026:

- Người dùng chọn chế độ MANUAL.
- Nhập thời gian tưới 3 giây.
- Dashboard cho phép nhập giá trị này.
- Khi gửi lệnh, hệ thống từ chối.

Thông báo:

“Thời gian tưới vượt giới hạn an toàn 1000 ms. Yêu cầu bị từ chối.”

**Nguyên nhân cần điều tra:**

Giới hạn thời gian giữa giao diện, Backend và cấu hình thiết bị chưa được đồng bộ.

**Yêu cầu chỉnh sửa:**

1. Kiểm tra cấu hình thời gian tưới tối đa trong Firmware.
2. Kiểm tra giới hạn thời gian tại Backend.
3. Kiểm tra giới hạn của ô nhập liệu trên Dashboard.
4. Đồng bộ các giới hạn theo cấu hình an toàn thực tế.
5. Không cho người dùng gửi thời gian vượt giới hạn.
6. Hiển thị rõ thời gian tưới tối đa.
7. Cải thiện thông báo lỗi bằng tiếng Việt dễ hiểu.

**Ví dụ giao diện mong muốn:**

Thời gian tưới thủ công: 0,5 giây.

Giới hạn cho phép: 0,1–1 giây.

Nếu nhập vượt giới hạn, hiển thị:

“Thời gian tưới tối đa hiện tại là 1 giây. Vui lòng nhập lại.”

**Lưu ý:** Không tự động tăng giới hạn an toàn của Backend hoặc Firmware chỉ để chấp nhận giá trị 3 giây.

**Tiêu chí hoàn thành:**
- Dashboard không gửi yêu cầu vượt giới hạn.
- Backend vẫn kiểm tra độc lập.
- Firmware vẫn giữ giới hạn an toàn.
- Các lệnh hợp lệ được thực hiện bình thường.

**Trạng thái: CHƯA SỬA.**

### 6.2.2. VẤN ĐỀ 02 – CẦN KIỂM TRA ĐỘ ỔN ĐỊNH CẢM BIẾN ĐỘ ẨM ĐẤT

**Mức độ ưu tiên: P1 – Cao**

**Hiện trạng:**

Trong quá trình kiểm thử, cảm biến từng hiển thị các giá trị:

- 0%.
- 28,98%.
- Khoảng 38–40%.
- 53,39%.
- 55,48%.
- 56,53%.

Có những thời điểm độ ẩm thay đổi rất nhanh.

**Vấn đề:**

Chưa xác định được toàn bộ thay đổi này là do thao tác thử cảm biến, môi trường đo hay sai số thiết bị.

Nếu tín hiệu không ổn định, AUTO có thể đưa ra quyết định tưới không phù hợp.

**Yêu cầu cải tiến:**

1. Kiểm tra giá trị ADC thô.
2. Kiểm tra hệ số hiệu chuẩn độ ẩm đất.
3. Đánh giá độ ổn định của cảm biến khi giữ nguyên vị trí.
4. Kiểm tra ảnh hưởng của nguồn điện và nhiễu.
5. Xem xét sử dụng bộ lọc trung vị hoặc trung bình trượt.
6. Không để một mẫu bất thường duy nhất gây kích hoạt bơm.
7. Phát hiện dữ liệu cảm biến không hợp lệ hoặc quá cũ.
8. Hiển thị cảnh báo nếu cảm biến mất kết nối hoặc có dấu hiệu bất thường.

**Lưu ý:** Firmware hiện đã có cơ chế kiểm tra nhiều mẫu trước khi kích hoạt AUTO; cần kiểm tra cơ chế đang chạy trước khi thay đổi.

**Tiêu chí hoàn thành:**
- Cảm biến ổn định khi điều kiện đo không thay đổi.
- Giá trị đo được hiệu chuẩn và có thể giải thích.
- AUTO không kích hoạt do nhiễu ngắn hạn.

**Trạng thái: CẦN ĐÁNH GIÁ THÊM.**

### 6.2.3. VẤN ĐỀ 03 – CẢI THIỆN THÔNG TIN TRẠNG THÁI ĐỒNG BỘ

**Mức độ ưu tiên: P3 – Thấp**

**Hiện trạng:**

Dashboard từng hiển thị:

“Cần kiểm tra – Còn 1 sự kiện chờ gửi.”

Sau đó, lúc 14:12:

- Trạng thái chuyển thành “Đã đồng bộ”.
- `queued_events = 0`.
- Không phát hiện lỗi lưu trữ.
- Đồng hồ hoạt động bình thường.

**Kết luận:** Không xác nhận đây là lỗi hệ thống. Không cần sửa cơ chế đồng bộ chỉ vì cảnh báo tạm thời này.

**Đề xuất cải thiện giao diện, nếu còn thời gian:**
- Phân biệt “Đang đồng bộ” và “Đồng bộ thất bại”.
- Hiển thị số sự kiện đang chờ.
- Chỉ cảnh báo nghiêm trọng khi sự kiện tồn đọng quá lâu hoặc đồng bộ thất bại.
- Bổ sung thời điểm đồng bộ thành công gần nhất.

**Trạng thái: KHÔNG PHẢI LỖI BẮT BUỘC SỬA.**

### 6.2.4. VẤN ĐỀ 04 – CẦN KIỂM TRA CẤU HÌNH COOLDOWN VÀ NGÂN SÁCH AUTO

**Mức độ ưu tiên: P2 – Trung bình**

**Hiện trạng:**

Trong quá trình kiểm thử:

- AUTO đã chạy nhiều lần.
- Thời gian mỗi lần tưới khoảng 3 giây.
- Dashboard hiển thị ngân sách AUTO 20 giây.
- Khi ngân sách còn 2 giây, không ghi nhận lần tưới 3 giây tiếp theo.

**Yêu cầu:**

1. Xác nhận thời gian cooldown đang được nạp trên ESP32.
2. Đối chiếu cấu hình Firmware với thông tin Dashboard.
3. Kiểm tra thời điểm bắt đầu và kết thúc cooldown.
4. Xác nhận chính xác nguyên nhân từ chối tưới khi ngân sách không đủ.
5. Bổ sung thông tin thời gian chờ còn lại nếu có dữ liệu đáng tin cậy.
6. Kiểm tra cơ chế đặt lại ngân sách theo ngày.

**Tiêu chí hoàn thành:**
- Cooldown hoạt động đúng cấu hình.
- Không tưới trước khi hết cooldown.
- Không vượt ngân sách tưới.
- Dashboard hiển thị đúng giới hạn đang áp dụng.

**Trạng thái: HOẠT ĐỘNG THEO QUAN SÁT, CẦN ĐỐI CHIẾU CẤU HÌNH.**

---

## 6.3. CẢI TIẾN AN TOÀN PHẦN CỨNG

**Mức độ ưu tiên: P1 – Cao**

### 6.3.1. Bảo vệ mạch điều khiển máy bơm

Cần kiểm tra và hoàn thiện:

- Diode chống điện áp ngược cho động cơ DC.
- Tụ lọc nguồn phù hợp.
- Nguồn cấp riêng cho máy bơm.
- Dây dẫn và đầu nối.
- Cách điện và chống nước.
- Khả năng chịu dòng của relay.
- Trạng thái an toàn khi mất nguồn hoặc ESP32 reset.

Các linh kiện bảo vệ đã được thảo luận trước đó gồm diode 1N4007 và tụ 470 µF, nhưng cần kiểm tra lại sơ đồ đấu nối và thông số thực tế trước khi lắp.

### 6.3.2. Kiểm tra hiện tượng siphon

Trong quá trình thử nghiệm trước đó từng xuất hiện hiện tượng nước có thể tiếp tục chảy sau khi bơm ngừng.

**Yêu cầu:**
- Kiểm tra vị trí đầu ra ống nước.
- Bố trí chống tự chảy do chênh lệch cao độ.
- Đảm bảo ngắt bơm đồng nghĩa với ngừng cấp nước thực tế.

### 6.3.3. Kiểm tra vận hành lâu dài

Cần đánh giá:
- Nhiệt độ động cơ.
- Độ ổn định nguồn.
- Khả năng hoạt động sau nhiều chu kỳ.
- Hoạt động khi mất Wi-Fi.
- Hoạt động khi Backend không phản hồi.

**Trạng thái: CHƯA HOÀN THIỆN ĐÁNH GIÁ AN TOÀN DÀI HẠN.**

---

## 6.4. HOÀN THIỆN VÀ TÍCH HỢP AI

**Mức độ ưu tiên: P1 – Cao đối với mục tiêu đồ án AI**

### 6.4.1. Đánh giá tình trạng AI hiện tại

Hệ thống đã có các thành phần:

- API dự báo.
- Chức năng hiển thị dự báo.
- Lưu kết quả dự báo.
- Các mô hình Machine Learning.
- Chức năng đánh giá mô hình.

Các mô hình đã được đề cập gồm:

1. Persistence – giữ nguyên giá trị hiện tại.
2. Linear Extrapolation – ngoại suy tuyến tính.
3. Linear Regression.
4. Random Forest.

**Hạn chế hiện tại:**

Kết quả đánh giá được hiển thị từ dữ liệu giả lập và chưa đủ để kết luận mô hình hoạt động tốt trên dữ liệu cảm biến thực tế.

### 6.4.2. Thu thập và chuẩn bị dữ liệu thực tế

**Yêu cầu:**
- Sử dụng dữ liệu cảm biến đã lưu trong PostgreSQL.
- Kiểm tra thời gian lấy mẫu.
- Xử lý dữ liệu thiếu.
- Phát hiện giá trị bất thường.
- Phân biệt dữ liệu thật và dữ liệu giả lập.
- Phân biệt giai đoạn bơm hoạt động và không hoạt động.
- Tránh đưa dữ liệu tương lai vào đặc trưng đầu vào.

**Dữ liệu đầu vào dự kiến:**
- Độ ẩm đất.
- Nhiệt độ.
- Độ ẩm không khí.
- Ánh sáng.
- Thời gian.
- Lịch sử tưới.

### 6.4.3. Hoàn thiện dự báo độ ẩm đất

**Mục tiêu:** Dự báo độ ẩm đất trong khoảng 30–60 phút tiếp theo.

**Yêu cầu:**
1. Xây dựng bộ dữ liệu huấn luyện từ dữ liệu thực.
2. Tách dữ liệu huấn luyện và kiểm tra theo thời gian.
3. Đánh giá các mô hình trên cùng một tập kiểm tra.
4. So sánh với Persistence.
5. Sử dụng các chỉ số như MAE và RMSE.
6. Kiểm tra mô hình có thực sự tốt hơn baseline không.
7. Không lựa chọn mô hình phức tạp chỉ vì tên thuật toán.

**Nguyên tắc:** Nếu chưa có đủ dữ liệu thực tế để chứng minh mô hình tốt hơn Persistence, phải ghi rõ đây là mô hình thử nghiệm.

### 6.4.4. Cải thiện khả năng giải thích kết quả AI

Dashboard nên hiển thị:

- Độ ẩm đất hiện tại.
- Độ ẩm dự báo sau 30 phút.
- Độ ẩm dự báo sau 60 phút.
- Tên mô hình đang sử dụng.
- Thời điểm dự báo.
- Chất lượng hoặc độ tin cậy của dự báo, nếu đã được đánh giá.
- Cảnh báo khi dữ liệu không đủ hoặc đã cũ.

**Ví dụ cách trình bày:**

Độ ẩm hiện tại: 35%.

Dự báo sau 30 phút: 32%.

Dự báo sau 60 phút: 29%.

Xu hướng: Độ ẩm đang giảm.

Các số trên chỉ là ví dụ giao diện, không phải kết quả dự báo thực tế.

### 6.4.5. Tích hợp AI vào hệ thống tưới

**Nguyên tắc an toàn quan trọng:**

Không cho AI trực tiếp bật máy bơm ngay khi mới tích hợp.

Đề xuất triển khai theo ba giai đoạn.

**Giai đoạn 1 – AI chỉ dự báo**

- AI dự báo độ ẩm đất.
- Dashboard hiển thị kết quả.
- AUTO vẫn hoạt động theo ngưỡng.

**Giai đoạn 2 – AI đề xuất tưới**

- AI đưa ra đề xuất.
- Người dùng xem đề xuất trên Dashboard.
- AI chưa tự điều khiển bơm.

**Giai đoạn 3 – AI hỗ trợ điều khiển**

Chỉ thực hiện khi mô hình đã được đánh giá đầy đủ.

Ngay cả khi AI đề xuất tưới, ESP32 vẫn phải kiểm tra:
- Phao đủ nước.
- Dữ liệu cảm biến hợp lệ.
- Cooldown.
- Giới hạn thời gian tưới.
- Ngân sách tưới.
- Trạng thái STOP/OFF.
- Các điều kiện an toàn khác.

**Không được cho AI bỏ qua các cơ chế bảo vệ của Firmware.**

---

## 6.5. CẢI THIỆN GIAO DIỆN DASHBOARD

**Mức độ ưu tiên: P2 – Trung bình**

### 6.5.1. Khu vực giám sát cảm biến

Đề xuất:
- Hiển thị rõ trạng thái bình thường, cảnh báo và lỗi.
- Bổ sung thời điểm cập nhật dữ liệu.
- Cải thiện khả năng đọc biểu đồ.
- Hiển thị ngưỡng độ ẩm trực tiếp trên biểu đồ.
- Phân biệt dữ liệu cảm biến bị thiếu với giá trị 0% thực tế.

### 6.5.2. Khu vực điều khiển máy bơm

Đề xuất:
- Làm nổi bật chế độ OFF, MANUAL và AUTO.
- Hiển thị giới hạn thời gian tưới MANUAL.
- Hiển thị trạng thái đang tưới nếu ESP32 có dữ liệu xác nhận.
- Hiển thị thời gian chờ AUTO.
- Hiển thị ngân sách tưới còn lại.
- Làm nổi bật nút STOP.
- Hiển thị lý do không thể tưới.

**Ví dụ:**

“Không thể tưới: Phao báo thiếu nước.”

“Không thể tưới: Đang trong thời gian chờ.”

“Không thể tưới: Ngân sách tưới còn lại không đủ.”

### 6.5.3. Khu vực lịch sử hoạt động

Đề xuất:
- Lọc lịch sử theo AUTO/MANUAL.
- Lọc theo ngày.
- Phân biệt lý do dừng bơm.
- Hiển thị thời lượng thực tế.
- Xuất lịch sử phục vụ báo cáo.
- Phân biệt thời gian bơm với lượng nước thực tế.

### 6.5.4. Khu vực AI

Đề xuất:
- Tạo khu vực riêng cho dự báo AI.
- Hiển thị xu hướng độ ẩm đất.
- So sánh giá trị thực tế và dự báo.
- Hiển thị mô hình đang sử dụng.
- Cảnh báo khi AI chỉ đang chạy với dữ liệu giả lập.
- Phân biệt rõ “AI dự báo”, “AI đề xuất” và “AUTO điều khiển”.

### 6.5.5. Cải thiện trải nghiệm người dùng

Đề xuất:
- Thống nhất màu sắc và trạng thái.
- Tối ưu bố cục trên màn hình máy tính.
- Cải thiện hiển thị trên điện thoại.
- Thông báo lỗi rõ ràng.
- Tránh hiển thị thông tin kỹ thuật khó hiểu cho người dùng phổ thông.
- Giữ phần thông tin kỹ thuật chi tiết trong mục mở rộng.

---

## 6.6. KIỂM TRA BACKEND VÀ CƠ SỞ DỮ LIỆU

**Mức độ ưu tiên: P2 – Trung bình**

### Backend FastAPI

Cần kiểm tra:
- API nhận dữ liệu ESP32.
- API gửi lệnh điều khiển.
- API xác nhận kết quả lệnh.
- API lịch sử tưới.
- API dự báo AI.
- Xử lý lỗi mạng và timeout.
- Kiểm tra dữ liệu đầu vào.
- Phân quyền điều khiển thiết bị.

### PostgreSQL

Cần thực hiện:
- Kiểm tra dữ liệu cảm biến.
- Kiểm tra lịch sử tưới.
- Kiểm tra lịch sử lệnh.
- Kiểm tra dữ liệu dự báo.
- Kiểm tra dữ liệu trùng lặp.
- Backup và restore cơ sở dữ liệu.
- Chạy thử hệ thống từ môi trường sạch.

### Đồng bộ ESP32

Cần đảm bảo:
- Không mất sự kiện khi mất kết nối tạm thời.
- Không ghi trùng sự kiện khi gửi lại.
- Phân biệt lệnh đã nhận và lệnh đã thực hiện.
- Trạng thái thiết bị phản ánh đúng dữ liệu từ ESP32.

---

## 6.7. DANH SÁCH CÔNG VIỆC ƯU TIÊN

| STT | Công việc | Mức ưu tiên | Trạng thái |
|---|---|---|---|
| 01 | Sửa giới hạn thời gian MANUAL trên Dashboard | P1 | Chưa sửa |
| 02 | Kiểm tra độ ổn định cảm biến độ ẩm đất | P1 | Cần đánh giá |
| 03 | Hoàn thiện bảo vệ điện và chống siphon | P1 | Chưa hoàn thiện |
| 04 | Kiểm tra cấu hình cooldown và ngân sách AUTO | P2 | Cần xác nhận |
| 05 | Thu thập và làm sạch dữ liệu AI thực tế | P1 | Cần thực hiện |
| 06 | Đánh giá mô hình dự báo 30–60 phút | P1 | Chưa xác minh |
| 07 | Tích hợp dự báo AI với Dashboard | P1 | Đã có một phần |
| 08 | Xây dựng chức năng AI đề xuất tưới | P2 | Dự kiến |
| 09 | Cải thiện giao diện điều khiển | P2 | Dự kiến |
| 10 | Cải thiện biểu đồ và lịch sử | P2 | Dự kiến |
| 11 | Kiểm tra PostgreSQL và backup/restore | P2 | Chưa xác nhận |
| 12 | Kiểm tra toàn bộ hệ thống sau khi sửa | P1 | Chưa thực hiện |
| 13 | Chuẩn bị tài liệu, sơ đồ và demo | P1 | Cần hoàn thiện |
| 14 | AI tham gia điều khiển AUTO | P3 | Chỉ xem xét sau khi đánh giá an toàn |

---

## 6.8. YÊU CẦU ĐỐI VỚI TRỢ LÝ LẬP TRÌNH

Khi tiếp nhận dự án Smart Garden, cần tuân thủ các nguyên tắc sau:

**1. Không sửa các chức năng đã hoạt động tốt nếu không cần thiết.**

Các chức năng MANUAL, AUTO, STOP, Reset, phao nước và giới hạn tưới đã được thử nghiệm thực tế.

**2. Không tự ý thay đổi ngưỡng và giới hạn an toàn.**

Mọi thay đổi liên quan đến thời gian tưới, cooldown, ngân sách hoặc điều kiện bật bơm phải được giải thích và kiểm thử lại.

**3. Ưu tiên sửa lỗi đã xác nhận trước.**

Đặc biệt là lỗi không đồng nhất giới hạn MANUAL.

**4. Không sử dụng kết quả AI giả lập để khẳng định hiệu quả trên dữ liệu thật.**

Phải đánh giá bằng dữ liệu thực tế và so sánh với baseline.

**5. Không cho AI trực tiếp điều khiển máy bơm khi chưa kiểm chứng.**

Giữ nguyên các điều kiện bảo vệ ở ESP32.

**6. Mọi thay đổi phải có nhật ký.**

Cần ghi:
- File được sửa.
- Nội dung thay đổi.
- Lý do thay đổi.
- Kết quả kiểm thử.
- Các vấn đề còn tồn tại.

**7. Sau mỗi lần sửa phải kiểm thử hồi quy.**

Đảm bảo việc sửa giao diện hoặc tích hợp AI không làm hỏng các chức năng điều khiển đã hoạt động.

---

## 6.9. KẾ HOẠCH HOÀN THIỆN DỰ ÁN

**Giai đoạn 1 – Ổn định hệ thống**
- Sửa lỗi MANUAL.
- Kiểm tra cảm biến.
- Xác nhận cấu hình Firmware.
- Hoàn thiện bảo vệ phần cứng.

**Giai đoạn 2 – Hoàn thiện AI**
- Chuẩn bị dữ liệu thật.
- Huấn luyện và đánh giá mô hình.
- So sánh với Persistence.
- Tích hợp dự báo vào Dashboard.

**Giai đoạn 3 – Cải thiện giao diện**
- Cải thiện khu vực điều khiển.
- Cải thiện biểu đồ.
- Hoàn thiện lịch sử.
- Bổ sung khu vực dự báo AI.

**Giai đoạn 4 – Kiểm thử và bàn giao**
- Kiểm thử hồi quy.
- Kiểm tra Backend và PostgreSQL.
- Backup/restore.
- Chuẩn bị demo.
- Hoàn thiện báo cáo và tài liệu kỹ thuật.

---

## 6.10. KẾT LUẬN

Smart Garden đã hoàn thành được phần lớn chức năng điều khiển IoT cơ bản và có kết quả kiểm thử thực tế tích cực.

Trọng tâm phát triển tiếp theo không phải viết lại toàn bộ hệ thống mà là:

**Ổn định phần cứng và cảm biến → Sửa lỗi giao diện → Hoàn thiện dữ liệu và mô hình AI → Tích hợp dự báo → Kiểm thử hồi quy → Hoàn thiện demo.**

Hệ thống cần tiếp tục giữ các cơ chế an toàn độc lập trên ESP32. AI được xem là thành phần hỗ trợ dự báo và ra quyết định, không thay thế các điều kiện bảo vệ máy bơm.

**Trạng thái bàn giao:** Sẵn sàng chuyển sang giai đoạn sửa lỗi và phát triển tiếp theo, nhưng chưa được xác nhận an toàn cho vận hành tự động không giám sát dài hạn.