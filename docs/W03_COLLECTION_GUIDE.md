# W03 — quy trình thu phiên tiếp theo

W01 và W02 thuộc cùng một chu kỳ tưới. W03 nên ghi nhận chu kỳ tưới mới khi cây cần,
không tưới chỉ để đủ số mẫu. Giữ cùng thiết bị garden-01, cảm biến và calibration
soil-2511-979 để so sánh với W01. Nếu thay đổi phần cứng/hiệu chuẩn, ghi rõ và phân phiên.

## Chuẩn bị

1. Chạy PostgreSQL, backend và ESP32 theo cấu hình đã dùng để thu W02.
2. Giữ chế độ OFF để tránh tưới tự động ngoài nhật ký. Không nạp firmware hoặc thay
   cấu hình giữa phiên. Xác nhận mẫu mới có giờ đo hợp lệ và clock_ready=true.
3. Cố định vị trí/độ sâu cảm biến, vị trí chậu, ống và phao. Mạch phải khô và tránh nước.
4. Ghi ngày giờ Việt Nam bắt đầu phiên và thời điểm tưới gần nhất. Không lấy thời điểm
   bật máy làm thời điểm tưới. Nếu không rõ thì ghi chưa rõ.

## Thu dữ liệu

1. Nếu điều kiện cây cho phép, ghi 15–30 phút trước tưới để có mốc so sánh. Không trì hoãn
   việc chăm cây chỉ để đủ dữ liệu nền.
2. Khi cần tưới, dùng lượng nước phù hợp chậu/cây, đo bằng cốc chia vạch. Ghi riêng giờ
   bắt đầu, giờ kết thúc, lượng ml thực tế và cách tưới (tay/bơm). Không quy đổi muỗng
   thành ml hoặc dùng thời lượng relay làm lượng nước thực.
3. Để so sánh dữ liệu, có thể tiếp tục cách tưới tay của W01 trong lúc thiết bị OFF.
   Nếu dùng bơm, chỉ dùng cấu hình đã nghiệm thu và ghi lượng nước thực đo.
4. Giữ nguyên vị trí và theo dõi sau tưới. Mục tiêu kế hoạch là 8–12 giờ; có thể kéo dài
   đến 24 giờ nếu điều kiện thu ổn định. Số giờ không bảo đảm có đủ một chu kỳ khô–tưới.
5. Ghi mọi lần tưới bổ sung, reset/mất điện, mất mạng, dịch chuyển cảm biến/chậu,
   đổi vị trí ánh sáng hoặc khoảng không theo dõi được. Không bỏ qua sự cố để làm dữ liệu đẹp.
6. Giữ máy không sleep khi đang thu qua backend local. Không cần mở thêm Serial Monitor.

## Kết thúc

Ghi thời điểm dừng thực tế, xác nhận mẫu cuối đã lưu trong PostgreSQL. Không xóa dữ liệu
W01/W02 hoặc reset bộ đếm. Gửi nhật ký sau để xuất snapshot riêng:

| Nội dung | Giá trị cần ghi |
|---|---|
| Ngày thu | YYYY-MM-DD |
| Bắt đầu / kết thúc (UTC+07) | HH:MM / HH:MM |
| Lần tưới trước phiên | Ngày giờ hoặc chưa rõ |
| Tưới trong phiên | Bắt đầu–kết thúc, ml, tay/bơm cho từng lần |
| Reset/mất điện/mất mạng | Giờ và diễn biến, hoặc không phát hiện |
| Di chuyển/thay đổi điều kiện | Chi tiết, hoặc không |
| Khoảng không theo dõi được | Mốc giờ, hoặc không |

## Đánh giá sau thu

Giữ cố định candidate W01, kiểm tra W03 bằng cùng feature và bộ lọc, đối chiếu baseline.
Nếu dùng W02/W03 để chỉnh mô hình, chúng trở thành dữ liệu phát triển; cần phiên tương lai
chưa sử dụng để đánh giá cuối. Không bật điều khiển tưới bằng AI từ kết quả một phiên.
