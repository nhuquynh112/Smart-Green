# BÀN GIAO PHIÊN THU DỮ LIỆU W04
## Dự án Smart Garden – IoT + AI

**Ngày thực hiện:** 14/11/2026  
**Phiên:** W04 – Real Plant Watering Session  
**Trạng thái:** Đã kết thúc thu thập, chờ xử lý dữ liệu và đánh giá AI.

---

## 1. THÔNG TIN HỆ THỐNG

| Thành phần | Thông tin |
|---|---|
| Dự án | Smart Garden / Smart-Green |
| GitHub | https://github.com/nhuquynh112/Smart-Green |
| Nhánh làm việc | `tv1/firmware-ai-foundation` |
| Thiết bị | ESP32 |
| Device ID | `garden-01` |
| Cây thử nghiệm | Cẩm nhung (Fittonia) |
| Đường kính chậu | Khoảng 9 cm |
| Database | PostgreSQL |
| Database name | `smart_green_local` |
| Bảng dữ liệu | `public.telemetry` |
| Data origin | `real` |
| Calibration ID | `soil-2511-979` |
| Chế độ điều khiển | OFF |
| Máy bơm | Không sử dụng trong phiên |
| Phương pháp tưới | Thủ công |

Các cảm biến đang sử dụng:
- Độ ẩm đất.
- Nhiệt độ không khí DHT22.
- Độ ẩm không khí DHT22.
- Cảm biến ánh sáng ADC.
- Phao báo mực nước.

**Lưu ý:** `soil_pct` là chỉ số độ ẩm tương đối được hiệu chuẩn từ cảm biến, không phải phần trăm nước tuyệt đối trong đất.

Giá trị ánh sáng trên Dashboard là ADC thô, chưa được quy đổi sang lux.

---

## 2. THỜI GIAN THU DỮ LIỆU W04

| Nội dung | Thời gian |
|---|---|
| Ngày thu | 14/11/2026 |
| Bắt đầu | **10:15 ICT (UTC+7)** |
| Bản ghi đầu tiên | 10:15:44 |
| Kết thúc | **21:12 ICT (UTC+7)** |
| Tổng thời gian | Khoảng 10 giờ 57 phút |
| Số mẫu thô | **1.313 mẫu** |
| Thiết bị | `garden-01` |

Dữ liệu được xác nhận bằng truy vấn PostgreSQL tại thời điểm kết thúc phiên.

**Câu SQL truy xuất W04:**

```sql
SELECT *
FROM public.telemetry
WHERE device_id = 'garden-01'
  AND received_at >= '2026-11-14 10:15:00+07'
  AND received_at <= '2026-11-14 21:12:00+07'
ORDER BY received_at ASC;
```

Kết quả pgAdmin: **1.313 dòng**.

Lưu ý: Tổng số mẫu thô chưa phải số phút hợp lệ sau xử lý.

---

## 3. TÌNH TRẠNG CÂY TRƯỚC TƯỚI

Buổi sáng ngày 14/11:

- Lá cây vẫn tươi.
- Bề mặt đất không quá khô.
- Khi dùng que kiểm tra sâu khoảng 1–2 cm, đất được xác nhận là khô.
- Không ghi nhận cây bị héo.
- Không thay đổi vị trí cảm biến trong quá trình thu thập.

Quyết định tưới dựa trên việc kiểm tra đất thực tế, không chỉ dựa vào chỉ số `soil_pct`.

---

## 4. NHẬT KÝ TƯỚI NƯỚC W04

**W04 có hai sự kiện tưới thủ công riêng biệt.**

### Sự kiện tưới 1

| Thuộc tính | Giá trị |
|---|---|
| Ngày | 14/11/2026 |
| Bắt đầu | Khoảng 12:00 |
| Kết thúc | **12:01** |
| Lượng nước | 2 muỗng cà phê |
| Thể tích ước tính | 10 mL |
| Phương pháp | Tưới thủ công quanh gốc |
| AUTO | OFF |
| Máy bơm | OFF |

### Sự kiện tưới 2

| Thuộc tính | Giá trị |
|---|---|
| Ngày | 14/11/2026 |
| Bắt đầu | Khoảng 12:20 |
| Kết thúc | Khoảng 12:21 |
| Lượng nước | **3 muỗng cà phê** |
| Thể tích ước tính | 15 mL |
| Phương pháp | Tưới thủ công quanh gốc |
| AUTO | OFF |
| Máy bơm | OFF |

**Tổng lượng nước W04: 5 muỗng cà phê ≈ 25 mL.**

Thể tích tính theo giả định 1 muỗng cà phê = 5 mL. Không có phép đo thể tích độc lập bằng dụng cụ chia vạch.

**Quan trọng:** Hai lần tưới cách nhau khoảng 20 phút. Phải xử lý thành hai sự kiện, không gộp thành một sự kiện 25 mL.

Thời điểm kết thúc lần tưới thứ hai chưa được người thực hiện xác nhận chính xác đến phút; khoảng 12:20–12:21 được suy ra từ trao đổi và ảnh Dashboard.

---

## 5. DỮ LIỆU CẢM BIẾN THEO CÁC MỐC QUAN TRỌNG

| Thời gian | Soil (%) | Nhiệt độ (°C) | Độ ẩm KK (%) | Ánh sáng (ADC) |
|---|---:|---:|---:|---:|
| 10:16 | 4,11 | 31,5 | 68,8 | 1.699 |
| 11:50 | 1,83 | 32,3 | 62,4 | 815 |
| 12:00 | 3,33 | 32,6 | 62,4 | 897 |
| 12:05 | 2,61 | 32,7 | 62,2 | 917 |
| 12:20 | 2,87 | 32,7 | 65,9 | 1.473 |
| 12:21 | **21,21** | 32,7 | 65,9 | 1.317 |
| 12:30 | 15,34 | 32,6 | 64,1 | 2.195 |
| 21:11 | 9,53 | 31,3 | 70,1 | 2.913 |

Các giá trị trên được ghi nhận từ ảnh Dashboard trong quá trình thu W04.

**Lưu ý:** Đây là những mốc quan sát thủ công, không thay thế dữ liệu gốc trong PostgreSQL.

---

## 6. DIỄN BIẾN ĐỘ ẨM ĐẤT SAU TƯỚI

### Giai đoạn 1 – Trước tưới

10:15–12:00:

- Độ ẩm đất dao động ở mức thấp.
- 11:50 ghi nhận 1,83%.
- Ngay trước tưới lúc 12:00 ghi nhận 3,33%.

### Giai đoạn 2 – Sau lần tưới thứ nhất

12:00–12:20:

- Tưới khoảng 10 mL.
- 12:05 độ ẩm hiển thị 2,61%.
- 12:20 độ ẩm hiển thị 2,87%.

Chưa ghi nhận mức tăng rõ rệt tại các mốc Dashboard được chụp.

Có thể nước chưa phân bố đến vùng cảm biến, nhưng cần phân tích dữ liệu gốc trước khi kết luận.

### Giai đoạn 3 – Sau lần tưới thứ hai

12:20–12:30:

- Tưới thêm khoảng 15 mL.
- 12:21 độ ẩm tăng lên 21,21%.
- 12:30 giảm còn 15,34%.

Chỉ số tăng **18,34 điểm phần trăm** từ mốc 12:20 đến 12:21.

### Giai đoạn 4 – Theo dõi sau tưới

12:30–21:11:

- Không có lần tưới bổ sung nào được báo cáo.
- 21:11 độ ẩm hiển thị 9,53%.
- Hệ thống vẫn hoạt động, chế độ OFF.

Diễn biến này có thể dùng để nghiên cứu phản ứng cảm biến sau tưới và quá trình thay đổi độ ẩm theo thời gian.

Không được mặc định toàn bộ mức giảm là do bay hơi nước; cần xem xét sự phân bố nước, vị trí cảm biến và nhiễu đo.

---

## 7. TÌNH TRẠNG DỮ LIỆU VÀ CHẤT LƯỢNG

Đã xác nhận:

- PostgreSQL truy xuất được 1.313 bản ghi.
- Device ID là `garden-01`.
- Dữ liệu có `data_origin = real` trong các dòng hiển thị.
- Calibration ID hiển thị là `soil-2511-979`.
- Truy vấn SQL thực hiện thành công.
- Dashboard vẫn cập nhật đến cuối phiên.

**Chưa xác nhận:**

- Số phút hợp lệ sau khi gộp dữ liệu.
- Số mẫu trùng.
- Khoảng thời gian thiếu dữ liệu.
- Số mẫu lỗi hoặc không hợp lệ.
- Số cửa sổ dự đoán 30/60 phút.
- Giá trị MAE trên W04.
- Độ đầy đủ của trường ánh sáng trong PostgreSQL.

Các chỉ tiêu này phải tính từ CSV thực tế, không được tự suy đoán.

---

## 8. YÊU CẦU XỬ LÝ AI W04

### Bước 1 – Bảo toàn dữ liệu

- Lưu CSV gốc.
- Không chỉnh sửa trực tiếp bản gốc.
- Kiểm tra số dòng, cột, timestamp, calibration và nguồn dữ liệu.
- Lưu checksum SHA-256.

### Bước 2 – Xử lý sự kiện tưới

Bổ sung nhật ký:

**Water event 1:**
- Start: 2026-11-14 12:00 ICT.
- End: 2026-11-14 12:01 ICT.
- Volume: approximately 10 mL.
- Method: manual.

**Water event 2:**
- Start: approximately 2026-11-14 12:20 ICT.
- End: approximately 2026-11-14 12:21 ICT.
- Volume: approximately 15 mL.
- Method: manual.

Các thời điểm có sai số cần được ghi rõ trong metadata.

**Không tự ý ghi hai sự kiện tưới thành lệnh điều khiển bơm ESP32.**

### Bước 3 – Chuẩn hóa dữ liệu

- Kiểm tra timestamp và múi giờ.
- Gộp dữ liệu theo phút.
- Kiểm tra các khoảng thiếu.
- Đánh dấu các thời điểm tưới.
- Không nội suy tùy tiện qua sự kiện tưới.

### Bước 4 – Đánh giá AI

Sử dụng mô hình W01 đã đóng băng, không huấn luyện lại trong bước đánh giá.

Đánh giá:
- Dự đoán 30 phút.
- Dự đoán 60 phút.
- MAE.
- Baseline Persistence.
- Các cửa sổ không có tưới trong khoảng dự đoán.

**Chú ý:** Hai sự kiện tưới cách nhau khoảng 20 phút nên không thể coi khoảng 12:01–12:20 là một đoạn khô liên tục đủ dài cho mọi cửa sổ dự đoán.

Cần xử lý đúng quy tắc `supervised()` và `minutes_since_water` trong mã AI hiện tại.

### Bước 5 – So sánh W01–W04

Đối chiếu với kết quả đã biết:

| Phiên | Nội dung |
|---|---|
| W01 | Thu dữ liệu sau tưới, huấn luyện mô hình |
| W02 | Theo dõi khô tự nhiên, đánh giá mô hình đóng băng |
| W03 | Tiếp tục theo dõi, đánh giá mô hình đóng băng |
| W04 | Chu kỳ tưới mới, có hai sự kiện tưới |

W04 là cơ hội kiểm tra mô hình trên một chu kỳ tưới mới, nhưng vẫn sử dụng cùng cây, chậu và cảm biến nên không phải thử nghiệm trên cây độc lập.

---

## 9. KẾT QUẢ AI W01 ĐỂ ĐỐI CHIẾU

**W01 – Test:**

- Horizon 30 phút: Persistence MAE = 0,4805.
- Horizon 60 phút: Random Forest MAE = 0,8017.

**W02 – Frozen W01 evaluation:**

- Horizon 30 phút: MAE = 0,302.
- Horizon 60 phút: Random Forest MAE = 1,852.
- Horizon 60 phút: Persistence MAE = 0,465.

**W03 – Theo báo cáo đã kiểm tra trước đó:**

- Persistence 30 phút: MAE = 0,3286.
- Persistence 60 phút: MAE = 0,4544.
- Random Forest 60 phút: MAE = 0,9557.

**W04:** Chưa có kết quả AI. Phải tính sau khi xử lý CSV.

---

## 10. VẤN ĐỀ CẢM BIẾN ÁNH SÁNG

Cảm biến ánh sáng đã hoạt động và hiển thị ADC trên Dashboard.

Ví dụ W04:
- 10:16: 1.699 ADC.
- 12:20: 1.473 ADC.
- 12:30: 2.195 ADC.
- 21:11: 2.913 ADC.

Hiện chưa xác nhận đầy đủ dữ liệu ánh sáng có được lưu trong PostgreSQL hay không.

Yêu cầu sau W04:

1. Kiểm tra trường ánh sáng trong dữ liệu gốc.
2. Bổ sung lưu trữ nếu còn thiếu.
3. Hiển thị và cảnh báo ánh sáng phù hợp.
4. Thử tích hợp ánh sáng vào AI.
5. So sánh mô hình có và không có ánh sáng trên cùng bộ dữ liệu đánh giá.

Không được tự quy đổi ADC sang lux nếu chưa hiệu chuẩn.

---

## 11. CÁC FILE CẦN TẠO SAU XỬ LÝ

Đề xuất:

- `W04_2026-11-14.csv` – dữ liệu gốc.
- `W04_water_events.json` – nhật ký hai lần tưới.
- `W04_quality_report.json` – chất lượng dữ liệu.
- `W04_predictions_30.csv` – dự đoán 30 phút.
- `W04_predictions_60.csv` – dự đoán 60 phút.
- `AI_EVAL_W04_2026-11-14.md` – kết quả đánh giá.
- `REAL_SESSION_W04_2026-11-14.md` – báo cáo phiên.
- Manifest SHA-256 – kiểm tra tính toàn vẹn.

Tên file có thể điều chỉnh theo cấu trúc hiện tại của repository để thống nhất W01–W03.

---

## 12. YÊU CẦU ĐỐI VỚI TRỢ LÝ XỬ LÝ W04

Hãy tiếp tục xử lý phiên W04 của dự án Smart Garden trên nhánh `tv1/firmware-ai-foundation`.

Dữ liệu thực tế được thu ngày 14/11/2026, từ 10:15 đến 21:12, gồm 1.313 bản ghi PostgreSQL.

Phiên có hai sự kiện tưới thủ công:
- 12:00–12:01: khoảng 10 mL.
- 12:20–12:21: khoảng 15 mL.

Tổng lượng nước khoảng 25 mL.

Yêu cầu:

1. Kiểm tra CSV gốc.
2. Kiểm tra chất lượng dữ liệu.
3. Ghi nhận chính xác hai sự kiện tưới.
4. Đánh giá mô hình W01 đóng băng trên W04.
5. So sánh với Persistence.
6. Phân tích phản ứng độ ẩm đất sau tưới.
7. Viết báo cáo và lưu minh chứng.
8. Chuẩn bị commit/push lên GitHub nhánh TV1.

**Không tự tạo số liệu AI hoặc kết luận khi chưa chạy đánh giá thực tế.**

**Không bật bơm tự động trong quá trình xử lý dữ liệu.**

---

## 13. KẾT LUẬN BÀN GIAO

Phiên W04 ngày 14/11/2026 đã hoàn thành thu thập dữ liệu thực tế.

**Thông tin quan trọng nhất:**

- 1.313 bản ghi thô.
- Khoảng 10 giờ 57 phút thu thập.
- Hai sự kiện tưới thủ công.
- Tổng lượng nước khoảng 25 mL.
- Độ ẩm tăng rõ sau lần tưới thứ hai.
- ESP32 và PostgreSQL hoạt động đến cuối phiên.
- Chưa có kết quả đánh giá AI W04.

**Trạng thái cuối cùng: W04 DATA COLLECTION COMPLETE – DATA PROCESSING PENDING.**