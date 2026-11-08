# Kế hoạch TV1 và đánh giá tổng quát

## Phạm vi đã thống nhất

Cập nhật 08/11/2026: đã kiểm thử cảm biến, relay/bơm có giám sát và hiệu chuẩn đất. Runtime telemetry-only đã nạp lên ESP32, đọc cảm biến, kết nối Wi-Fi/NTP và thu log local; phiên 01 có 20 mẫu hợp lệ. Chưa nghiệm thu backend thật, tưới tự động hoặc AI trên dữ liệu thực nghiệm. Không mặc định ngày mua là ngày bắt đầu kế hoạch 14 ngày.

## Đối chiếu 14 ngày và phần có thể làm trong lúc thu dữ liệu

Nguồn: [kế hoạch phân công gốc](https://docs.google.com/document/d/1zqJXdOpc7KbatUblwYpyzUbmqkoZIC48Jc75ogRZkCc/edit), đối chiếu ngày 08/11/2026. Trạng thái dưới đây là phần TV1; không xác nhận phần TV2 đã hoàn thành.

| Ngày | Phần đã có | Còn làm / phụ thuộc |
| --- | --- | --- |
| 1 | Chân GPIO, cấu trúc dữ liệu, sơ đồ chức năng | Hoàn thiện sơ đồ điện theo module thực tế và chốt server với TV2 |
| 2 | Đọc cảm biến, hai mốc hiệu chuẩn, thử relay/bơm | Tiếp tục theo dõi độ ổn định; không đồng nghĩa đã thử điều khiển tự động |
| 3 | Wi-Fi/NTP, log local, chu kỳ 30 giây theo yêu cầu mới | API và PostgreSQL thật, đối chiếu bản ghi, thử mất mạng cùng TV2 |
| 4 | Auto-Rule/hysteresis/giới hạn và kiểm thử offline | Rà soát độ bao phủ ca thử trên máy được; xác minh tác động thật sau phiên thu |
| 5 | Guard lỗi, tài liệu nghiệm thu | Chuẩn bị bảng đo được ngay; đo lưu lượng và chốt hạn mức cần bơm thật |
| 6 | Parser, đặc trưng v2, hai baseline, Linear Regression | Pipeline đã chạy synthetic; xử lý phiên thật sau khi logger kết thúc |
| 7 | Kiểm tra readiness; hỗ trợ horizon 30/60 phút | Chuẩn bị tiêu chí chọn horizon được ngay; quyết định thực nghiệm cần dữ liệu nhiều chu kỳ |
| 8 | Random Forest, MAE và so sánh baseline trên synthetic | Cần dữ liệu thật để đánh giá; không cần chạy lại demo chỉ để tăng số lần thử |
| 9 | Chọn bằng validation, lưu model/metadata, hàm predict | Model thật chờ dữ liệu; chạy server chờ TV2 |
| 10 | Kiểm tra ID/hạn lệnh/guard trong mã và mock | Rà soát offline được; nhận lệnh AI và tưới thật cần TV2 cùng phần cứng |
| 11 | Chống trùng, fallback và ca thử replay/reset mô phỏng | Nghiệm thu reset/mạng/NVS thật; chưa đóng băng tích hợp |
| 12 | Checklist và ca thử lỗi offline | Có thể lập bảng truy vết yêu cầu → test → bằng chứng; thử lỗi thật làm sau phiên thu |
| 13 | Báo cáo nháp, sơ đồ, kết quả synthetic và phiên 01 | Soạn kịch bản video/demo, dàn ý thuyết trình ngay; số liệu thật và quay video chờ nghiệm thu |
| 14 | Có hướng dẫn và checklist phần cứng | Soạn trình tự demo/dự phòng được; kiểm tra nguồn/dây và tập demo cần mô hình, TV2 |

Ưu tiên công việc độc lập tiếp theo: (1) bảng truy vết yêu cầu–kiểm thử cho ngày 4/10/11/12; (2) kế hoạch đánh giá dữ liệu thật và chọn 30/60 phút cho ngày 7–9; (3) kịch bản demo/video cho ngày 13–14. Không cần mở cổng Serial, đổi cấu hình hoặc tác động vào file phiên đang ghi để làm các việc này.

Đã thực hiện phần chuẩn bị trên trong lượt tiếp theo ngày 08/11:

- [Ma trận kiểm thử](TV1_TEST_TRACEABILITY.md), bổ sung sáu nhóm test biên an toàn chạy trên máy tính và đã đạt.
- [Kế hoạch đánh giá AI thật](REAL_AI_EVALUATION_PLAN.md), gồm chọn horizon và bảo vệ tập test cuối.
- [Kịch bản demo/video và dàn ý thuyết trình](TV1_DEMO_SCRIPT.md).

Các tài liệu/test này không nâng trạng thái nghiệm thu phần cứng hoặc AI thực nghiệm.

Kiến trúc một chậu, ESP32 tự quyết định an toàn; FastAPI/PostgreSQL/Web do TV2 phụ trách; TV1 sở hữu cảm biến, điều khiển, dữ liệu đầu vào, huấn luyện và đánh giá AI. Hai bên cùng chịu trách nhiệm API, xác nhận thực thi và kiểm thử toàn hệ thống.

## Các điều chỉnh cần đưa vào kế hoạch gốc

1. Ngày 6 chỉ cam kết pipeline AI hoạt động, chưa cam kết thắng baseline. Số dòng/phút không thay thế số chu kỳ khô–tưới độc lập.
2. Dự đoán độ ẩm tương đối sau 30 phút **nếu không tưới thêm**. Chỉ mở rộng 60 phút khi dữ liệu hỗ trợ. Không gọi chỉ số 0–100 là độ ẩm thể tích.
3. Auto-Rule luôn là nền an toàn trong AUTO; mất mạng không làm mất nó. OFF/MANUAL không tự đổi sang AUTO khi mất mạng. Đây là làm rõ yêu cầu mất liên lạc 60 giây.
4. AI chỉ đề xuất tưới sớm; phải kiểm tra cảm biến mới, mức nước, thời gian nghỉ, giới hạn xung và hạn mức trước khi thực thi.
5. Bổ sung phương án phát hiện hết nước vào BOM hoặc bỏ tiêu chí tự phát hiện. Chưa có phần cứng thì không được giả định `tankOK=true` trong bản vận hành.
6. Kiểm thử từng phần từ đầu; ngày 12 dành cho nghiệm thu tổng thể. Báo cáo viết dần, không để toàn bộ tới ngày 13.

## Trình tự sau khi có linh kiện

| Mốc | TV1 thực hiện | Điều kiện hoàn thành |
|---|---|---|
| 1 | Kiểm tra BOM, nguồn, chân, chốt API với TV2 | Có sơ đồ theo đúng linh kiện thật |
| 2–3 | Driver cảm biến, hiệu chuẩn, thử bơm ngắn có giám sát, thu dữ liệu | Có log raw + hiệu chuẩn + bản tin nhận ở backend |
| 4–5 | Auto-Rule, thời gian nghỉ, giới hạn bơm, lỗi cảm biến/nguồn | Các tình huống an toàn được đo kiểm |
| 6–7 | Kiểm tra dữ liệu, baseline, mô hình đầu | Chạy lại được bằng lệnh, có báo cáo chất lượng dữ liệu |
| 8–9 | Đánh giá theo thời gian, lựa chọn bằng validation, tích hợp hàm predict | Có test riêng chưa dùng chọn mô hình |
| 10–11 | AI ở chế độ quan sát, xét điều kiện kích hoạt, tích hợp ACK | Chống trùng/hết hạn/reset có bằng chứng |
| 12–14 | Nghiệm thu, số liệu thật, video, báo cáo | Phân biệt rõ đạt/chưa đạt và giới hạn |

## Giới hạn của bản khung hiện tại

- Đã chạy cảm biến/Wi-Fi/NTP trên runtime thật; HTTP với backend thật và guard điều khiển bơm chưa nghiệm thu. Guard không phải mạch ngắt nguồn phần cứng.
- Hạn mức là cửa sổ 24 giờ bắt đầu tại lần tưới đầu tiên, **không phải** mọi cửa sổ trượt 24 giờ. Phải đánh giá giới hạn sát ranh giới cửa sổ trước khi nghiệm thu.
- Reset sẽ tắt trạng thái pumping, giữ phần thời gian đã dự trù và chờ lại đủ cooldown. Chưa biết giờ UTC sau khởi động thì khóa tưới. Cần chọn giải pháp giờ cho mất điện+mất mạng: RTC hoặc quy trình khởi động lại có giám sát.
- Khi reset giữa lần tưới, thời gian thực tế là không biết, sự kiện có reason Reboot; không diễn giải actualMs=0 là không tưới.
- Nhật ký 32 sự kiện đầy sẽ chặn lần tưới mới; cơ chế gửi/ACK đã viết nhưng còn phải thử với backend và mất mạng dài ngày.
- `tick()` phải được gọi thường xuyên. Giới hạn thời gian trong core không bảo vệ được khi task bị treo; trước nối bơm cần bộ ngắt/giám sát độc lập, mức OFF phần cứng và đo độ trễ.
- Lưu cấu trúc NVS là định dạng prototype, không phải định dạng nâng cấp bền vững; thay layout phải đổi version và có quy trình chuyển dữ liệu, không xóa hạn mức âm thầm.

## Bằng chứng phải có khi bảo vệ

Sơ đồ điện thật; bảng hiệu chuẩn cảm biến và lưu lượng; dữ liệu raw; nhật ký tưới; cấu hình/version; script huấn luyện; bảng MAE với baseline; biểu đồ thực tế/dự đoán; biên bản lỗi; video; hướng dẫn chạy lại. Không lấy số liệu của repo tham khảo làm kết quả của nhóm.
