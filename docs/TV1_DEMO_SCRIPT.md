# Kịch bản demo và video TV1 — ngày 13–14

Bản chuẩn bị, chưa xác nhận demo toàn hệ thống đạt. Không thực hiện các bước tác động thiết bị trong phiên thu dữ liệu hiện tại.

## Trình tự demo khoảng 6 phút

| Thời lượng | Trình bày | Bằng chứng cần chuẩn bị |
| --- | --- | --- |
| 0:00–0:45 | Bài toán một chậu cẩm nhung, phân công TV1/TV2 | Sơ đồ chức năng và ảnh mô hình thật |
| 0:45–1:30 | Cảm biến, raw và chỉ số ẩm tương đối; chu kỳ Serial 3 giây, telemetry 30 giây | Dòng telemetry có timestamp, device/boot/sequence |
| 1:30–2:15 | Gửi dữ liệu và xem lịch sử | Cùng identity trên ESP32, API và PostgreSQL/dashboard; chỉ trình diễn khi tích hợp đã đạt |
| 2:15–3:15 | Tưới có giới hạn và một tình huống từ chối | Kết quả nghiệm thu, bình đong/khay hứng, phao; chỉ chạy bài đã thử trước với người giám sát |
| 3:15–4:30 | AI dự đoán 30 phút, đối chiếu hai baseline | Biểu đồ thực tế/dự đoán và MAE thật; nếu chỉ có synthetic phải ghi rõ |
| 4:30–5:15 | Lệnh trùng/mất mạng và giới hạn | Video hoặc log đã nghiệm thu, không tạo lỗi điện ngẫu hứng |
| 5:15–6:00 | Phần đạt, chưa đạt và hướng phát triển | Checklist có bằng chứng, không quy đổi thành phần trăm tiết kiệm nước chưa đo |

## Mức demo theo bằng chứng

- **Chỉ thu local:** trình diễn cảm biến → JSONL → báo cáo chất lượng; nói rõ chưa có dữ liệu server. Đây là mức hiện có bằng chứng phiên 01.
- **Có backend:** thêm API/DB/dashboard sau khi TV2 và TV1 đối chiếu được bản ghi thật.
- **Có điều khiển:** chỉ thêm bơm sau nghiệm thu phần cứng, lưu lượng và các giới hạn.
- **Có AI:** nếu chỉ hiển thị đề xuất, ghi rõ mức dự phòng; chưa đạt toàn bộ mục tiêu AI kích hoạt tưới an toàn trong kế hoạch gốc.

Không dùng mock hoặc video cũ và giới thiệu là hệ thống đang chạy trực tiếp. Chuẩn bị video dự phòng có ngày quay và phiên bản, nêu rõ khi chuyển sang video.

## Danh sách cảnh quay

1. Toàn cảnh mô hình, chậu, cảm biến, nguồn và bình nước; không lộ mật khẩu.
2. Cận dữ liệu cảm biến và timestamp; giải thích soil_pct là tương đối.
3. Cùng bản ghi trên Serial và database/dashboard nếu đã tích hợp.
4. Bơm ngắn vào bình đo và OFF; kèm thời gian/volume đã đo, không diễn lại với giới hạn chưa xác minh.
5. Phao cạn hoặc lệnh từ chối theo ca đã nghiệm thu; quay trạng thái thiết bị và log cùng lúc.
6. Biểu đồ dự báo, baseline, MAE và giới hạn dữ liệu.

## Dàn ý thuyết trình

1. Vấn đề và phạm vi một chậu.
2. Kiến trúc, phân công và luồng dữ liệu.
3. Phần cứng, hiệu chuẩn và an toàn.
4. Firmware, nhận diện bản ghi và mất kết nối.
5. Dataset, nhật ký tưới và chất lượng thời gian.
6. AI, chia tập theo thời gian, baseline và MAE.
7. Thực nghiệm có bằng chứng; tách synthetic và dữ liệu thật.
8. Kết quả, phần chưa đạt và hướng phát triển.

## Trước buổi trình diễn

Đối chiếu [checklist phần cứng](TV1_HARDWARE_ACCEPTANCE.md), ghi commit/config không chứa bí mật, thống nhất vai trò với TV2, kiểm tra server và bản sao lưu. Kiểm tra đường nước, nguồn và mức OFF trước thử. Không cập nhật firmware ngay trước demo nếu chưa có thời gian nghiệm thu lại. Chuẩn bị bản log/biểu đồ/video local cho trường hợp mất mạng; lỗi thì nói rõ và dùng bằng chứng dự phòng.
