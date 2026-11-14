# Kế hoạch đánh giá AI bằng dữ liệu thật — ngày 7–9

Trạng thái 08/11/2026: chuẩn bị quy trình, chưa có kết quả huấn luyện thật. Giữ dự báo 30 phút làm mục tiêu chính; 60 phút là thử nghiệm phụ nếu dữ liệu hỗ trợ. Không chạy huấn luyện trong phiên thu hiện tại.

## 1. Chốt dữ liệu trước khi huấn luyện

Sau khi logger kết thúc, dùng [quy trình dataset](WATERING_AND_AI_DATASET.md) để kiểm tra JSONL và tổng hợp phút. Giữ raw, quality report, nhật ký tưới, commit mã, calibration ID và SHA256 dataset.

- Dùng giờ đo có múi giờ; mẫu chưa có NTP giữ thiếu. Giờ nhận proxy phải ghi rõ và không trộn vào tập dùng giờ đo.
- Xác nhận lịch sử tưới từ quan sát; không biết thời điểm tưới hôm trước thì giữ null.
- Ghi số phiên, khoảng thời gian, số chu kỳ khô–tưới, đổi boot, mẫu thiếu và cửa sổ hợp lệ. Số hàng không thay thế chu kỳ độc lập.
- Cửa sổ cần 15 phút lịch sử và 30/60 phút tương lai liên tục, không tưới bổ sung. Phút tưới, lỗi, reset và lịch sử không rõ bị loại theo builder.
- Một giờ lý tưởng chỉ tạo khoảng 15 cửa sổ dự báo 30 phút sau phần lịch sử; không đủ cho chia train/validation/test. Code yêu cầu ít nhất 150 cửa sổ trước chia và còn kiểm tra sau purge; đây chỉ là điều kiện kỹ thuật, không phải tiêu chuẩn đủ dữ liệu khoa học.

## 2. Chia tập và chọn phương án

Giữ thứ tự thời gian 60/20/20 theo pipeline hiện tại. Loại nhãn train/validation chạm ranh giới tập sau. Kiểm tra chu kỳ nào nằm ở từng tập; nhiều hàng cùng một chu kỳ vẫn tương quan. Khi bổ sung dữ liệu và đánh giá lại, ghi phiên bản thí nghiệm mới, không gọi tập test đã xem là dữ liệu chưa từng dùng.

So sánh persistence, ngoại suy tuyến tính, Linear Regression, Random Forest bằng cùng cửa sổ của từng horizon. Chọn model theo validation; baseline được phép thắng. Không lựa chọn dựa vào test cuối.

30 và 60 phút là hai bài toán khác nhau: không chọn 30 chỉ vì MAE tuyệt đối thường thấp hơn. Chọn horizon theo thời gian cần cảnh báo và độ bao phủ dữ liệu, ghi quyết định trước đánh giá cuối. So sánh từng horizon với baseline tương ứng. Nếu khảo sát cả hai, đánh dấu thí nghiệm khám phá và giữ một đợt dữ liệu tương lai mới để xác nhận lựa chọn.

Trainer hiện xuất cả validation và test trong một lần chạy. Chốt cấu hình trước khi chạy chính thức; không điều chỉnh dựa vào bảng test đã xuất. Nếu cần tuning nhiều lần, phải tách quy trình validation-only trước, hoặc thu một tập kiểm chứng mới sau tuning.

## 3. Kết quả phải báo cáo

| Nội dung | Cách ghi |
| --- | --- |
| Dữ liệu | Thời gian, số phiên/chu kỳ, calibration, time_basis, SHA256 |
| Chất lượng | Số phút/cửa sổ dùng được, thiếu/lỗi và phạm vi bị loại |
| Split | Số hàng, thời điểm đầu/cuối, thời điểm nhãn cuối từng tập |
| So sánh | Validation MAE và test MAE của cả bốn phương án, đơn vị điểm phần trăm |
| Đất khô dần | Số cửa sổ và MAE riêng khi target nhỏ hơn độ ẩm hiện tại |
| Hạn chế | Tương quan giữa cửa sổ, ít chu kỳ, phạm vi điều kiện, lịch sử tưới thiếu |
| Quyết định | Model/horizon được chọn, lý do và trạng thái chỉ quan sát |

Tập con đất khô dần được chọn bằng target đã quan sát, chỉ dùng phân tích hồi cứu, không phải điều kiện kích bơm. MAE không phải phần trăm accuracy hoặc bằng chứng tiết kiệm nước. Báo cáo theo từng chu kỳ/đợt nếu có đủ dữ liệu; không suy khoảng tin cậy từ giả định mọi phút độc lập.

## 4. Bàn giao model

Giữ `candidate.joblib`, `report.json`, `test_predictions.csv`; ghi phiên bản thư viện và `feature_version`. TV2 dùng cùng hàm tạo đặc trưng, calibration và time_basis. Chạy quan sát và so dự đoán với thực tế trước. Model tốt hơn baseline cũng không tự cấp quyền chạy bơm.

Xem [bàn giao AI](handoff/AI_INTEGRATION.md). Hiện ánh sáng được thu ở dạng raw nhưng chưa nằm trong danh sách đặc trưng model v2; nêu rõ điều này trong báo cáo, không tuyên bố model đã dùng tất cả cảm biến.
