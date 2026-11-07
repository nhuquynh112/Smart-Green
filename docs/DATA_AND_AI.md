# Dữ liệu và AI

## Bài toán

Ước lượng chỉ số ẩm tương đối sau 30 hoặc 60 phút nếu không có tưới bổ sung. Đây là mô hình có điều kiện; chưa chứng minh hiệu quả tiết kiệm nước hay khả năng điều khiển tốt hơn Auto-Rule.

CSV bắt buộc: timestamp, device_id, calibration_id, data_origin, soil_pct, temperature_c, humidity_pct, minutes_since_water, water_total_ms. Mỗi lần huấn luyện dùng đúng một thiết bị, một phiên bản hiệu chuẩn và một nguồn real/synthetic.

- Timestamp có timezone, quy về UTC. Giữ bản raw riêng.
- TV2 xuất dữ liệu ở lưới phút: gom trong phút UTC, timestamp là đầu phút; median các giá trị cảm biến hợp lệ trong phút, bộ đếm tại mẫu cuối. Chỉ xuất phút đã hoàn tất, không dùng giá trị phút kế tiếp. Sự kiện tưới được gán đúng phút; mọi phút đang tưới/không rõ sự kiện phải bị đánh dấu thiếu. Thời điểm dự báo là sau khi phút đã kết thúc, độ phân giải nhãn một phút.
- Không forward-fill hoặc nội suy qua khoảng mất mẫu. Core AI tự thêm phút trống và loại cửa sổ bị ảnh hưởng.
- Lỗi cảm biến là giá trị thiếu, không phải 0. `soil_pct` là thang tương đối sau hiệu chuẩn.
- `water_total_ms` tăng đơn điệu, không reset ngày; khi reset bộ đếm chia phiên dữ liệu. `minutes_since_water` tính từ lịch sử sự kiện, không biết thì để trống.
- Không trộn đất/chậu/vị trí cảm biến khác nhau dưới cùng calibration_id. Thu thập lặp lại trong nhiều chu kỳ và điều kiện, ghi lại mọi thay đổi.

## Quy trình

Đặc trưng: độ ẩm hiện tại, lag 5/15 phút, độ dốc 15 phút, nhiệt độ, độ ẩm không khí, thời gian từ tưới, giờ UTC sin/cos. Chưa có ánh sáng vì chưa chọn cảm biến; bổ sung phải đổi feature_version và huấn luyện lại.

Chỉ giữ 16 phút lịch sử đầy đủ, không tưới trong 15 phút gần nhất; tương lai phải đầy đủ và không tưới. Khi đang tưới hoặc vừa tưới, mô hình từ chối dự đoán; Auto-Rule chịu trách nhiệm điều khiển. MAE chỉ mô tả tập dry-down đã lọc; không gọi đó là MAE toàn bộ hoạt động.

Chia thời gian 60% train / 20% validation / 20% test, loại mẫu train/validation có thời điểm nhãn chạm ranh giới tập sau. Chọn mô hình bằng validation, giữ test cho báo cáo cuối. Cùng preprocessing, cùng tập đánh giá và clipping 0–100 cho tất cả mô hình. Không đổi mô hình lặp lại theo test; khi tinh chỉnh cần giữ đợt dữ liệu mới làm test cuối.

Baseline: giữ nguyên độ ẩm; ngoại suy tuyến tính từ 15 phút gần nhất. Mô hình: Linear Regression và Random Forest giới hạn độ sâu. Baseline được phép thắng. MAE tính bằng **điểm phần trăm của thang tương đối**, không phải % accuracy.

Ngưỡng >=150 cửa sổ trong code chỉ để tránh chia tập quá nhỏ khi smoke test, không xác nhận đủ dữ liệu khoa học. Cần báo cáo số chu kỳ, dải môi trường, tỷ lệ thiếu và sai số gần ngưỡng tưới. Khung hiện chưa tự tạo các phân tích theo chu kỳ hoặc khoảng tin cậy.

## Artefact

`report.json`: chất lượng dữ liệu, ranh giới tập, MAE, lựa chọn validation, phiên bản thư viện, SHA256 CSV và hạn chế. `test_predictions.csv`: nhãn và dự đoán cùng timestamp. `candidate.joblib`: model chọn + metadata, luôn chưa được phép điều khiển bơm.

Dữ liệu synthetic chỉ kiểm tra đường ống phần mềm, không mô phỏng chính xác đất. Không đổi nhãn synthetic thành real. Không tải model pickle/joblib không tin cậy. Nguồn chính thức: [scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html), [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).


## Kiểm tra đầu vào và đánh giá bổ sung (06/11/2026)

Dùng `python -m smart_green_ai.assess CSV --output REPORT.json` để báo các cột thiếu, giá trị thiếu và khả năng chia tập trước train. Không tự sửa dữ liệu hay chuyển received_at sang timestamp. Report train bổ sung `falling_soil_test`: số mẫu và MAE theo từng phương án khi target < soil hiện tại; đây là nhóm hồi cứu trong các cửa sổ không tưới, không phải điều kiện điều khiển. Hướng dẫn và kết quả kiểm thử tại TV1_AI_RUNBOOK.md.
