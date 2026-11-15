# Thử nghiệm ánh sáng — 15/11/2026

## Kết luận

**Chưa đề xuất thay mô hình đang dùng.** Thêm ánh sáng chưa giúp các mô hình học máy vượt Persistence trên W04. Không triển khai model, không gửi lệnh bơm và không thay firmware. Tất cả bundle thử nghiệm có `automatic_irrigation_approved=false`, `can_trigger_pump=false`, version riêng bị inference production v2 từ chối.

## Nguồn và quy tắc đã cố định trước khi chạy

Train toàn bộ cửa sổ đủ điều kiện W01; validation W02+W03; test W04. Không fit, chọn siêu tham số hoặc chọn đặc trưng bằng W04. W01–W03 cùng chu kỳ tưới nên validation chỉ độc lập về phiên/thời gian, không độc lập về chu kỳ. W04 thuộc chu kỳ mới nhưng cùng cây/chậu/cảm biến, và đã được xem trước ở lượt đánh giá cũ: đây là holdout mở rộng mang tính thăm dò, cần W05 chưa sử dụng để xác nhận.

So sánh LR/RF có và không có ánh sáng trên **cùng hàng train, validation, test**. RF cố định 150 cây, depth 8, leaf 10, seed 42; LR mặc định. Không random-split, không tuning sau khi xem W04. Có Persistence và ngoại suy tuyến tính. Bộ đối chứng mới fit toàn W01 khác mô hình W01 đóng băng cũ vốn fit phần train nội bộ; không nhầm hai loại kết quả.

Dùng CSV phút đã chốt làm nền, bổ sung median ADC từ raw JSONL theo timestamp thiết bị; không ghi đè raw hay CSV cũ. W03 chỉ dùng 956 mẫu đúng phiên. Một phút có ADC thiếu/không hợp lệ sẽ giữ NaN; không nội suy. Không dùng ADC tương lai để lọc cửa sổ. Giữ toàn bộ quy tắc loại phút tưới, mất dữ liệu, đổi boot và loại cửa sổ có tưới trong khoảng dự đoán của v2. W04 vẫn loại trước lần tưới đầu vì lịch sử trước phiên chưa được xác nhận.

5 đặc trưng thêm: ADC hiện tại, lag 5/15 phút, mean 15 phút gồm phút hiện tại và 14 phút trước, slope=(ADC hiện tại−lag15)/15. Cần 16 phút lịch sử đầy đủ. Giá trị phút chỉ khả dụng sau khi phút đóng; timestamp trong CSV là đầu bin như pipeline cũ. ADC 4095 giữ nguyên là giá trị bị giới hạn dải, không đổi sang lux, không coi là giá trị ánh sáng chính xác vượt trần. Có kịch bản nhạy cảm loại lịch sử chứa mẫu chạm trần, dùng nguyên model đã fit.

## Chất lượng ánh sáng

| Phiên | Mẫu | Có ADC | ADC=4095 | Tỷ lệ | Phút thiếu ADC |
|---|---:|---:|---:|---:|---:|
| W01 | 1062 | 1062 | 367 | 34.56% | 0 |
| W02 | 952 | 952 | 211 | 22.16% | 3 |
| W03 | 956 | 956 | 101 | 10.56% | 0 |
| W04 | 1313 | 1313 | 134 | 10.21% | 0 |

W02 có 3 phút thiếu ADC do không có telemetry ở các phút đó. 100% mẫu thô có ADC không đồng nghĩa chuỗi thời gian liên tục. `light_lux` không được suy ra. Thử che cảm biến garden-01 ngày 15/11: bình thường 688, che 2074, bỏ che 651; hỗ trợ chiều ADC tăng khi tối hơn trong lần thử, không hiệu chuẩn độ rọi và không xác định ngưỡng nhu cầu cây.

## MAE trên W04 (điểm phần trăm soil)

| Horizon | Số cửa sổ test | LR không sáng | LR có sáng | RF không sáng | RF có sáng | Persistence | Ngoại suy |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30 phút | 485 | 6.8029 | 6.9202 | 6.6132 | 6.6114 | 0.5729 | 0.9646 |
| 60 phút | 455 | 8.3732 | 7.9718 | 6.6246 | 6.6119 | 1.0045 | 1.7996 |

Validation chọn **Persistence cho cả 30 và 60 phút**. RF cải thiện rất nhỏ khi thêm ánh sáng, vẫn thua baseline rất xa; không chứng minh cải thiện có ý nghĩa thống kê từ các cửa sổ chồng lấn. Không báo khoảng tin cậy theo giả định từng cửa sổ độc lập.

## Phân tích RF tổng quát hóa kém

RF60 W01 cũ MAE≈6,625 so với Persistence≈1,005 trên W04; kết quả kiểm tra mới tương tự. Kiểm tra phạm vi fit/test ở từng đặc trưng được lưu trong report.json. Độ ẩm W04 sau tưới cao hơn vùng soil hiện tại đã học từ W01; RF dự đoán quanh vùng mục tiêu W01 thấp. Ánh sáng không tạo thêm nhãn soil cao hoặc thêm chu kỳ tưới cho train. Đây là bằng chứng phù hợp với lệch phân bố và thiếu đa dạng chu kỳ, chưa phải chứng minh nguyên nhân duy nhất. Không quy lỗi riêng cho cảm biến ánh sáng.

| Horizon | Train W01 | Validation W02 | Validation W03 | Test ngoài vùng soil fit |
|---|---:|---:|---:|---:|
| 30 | 483 | 385 | 433 | 485 |
| 60 | 453 | 325 | 403 | 455 |

## Độ nhạy với bão hòa

Giữ nguyên model, chỉ xét các cửa sổ W04 không có ADC chạm 4095 trong 16 phút lịch sử. Không dùng phân tích này để chọn model hay thay đổi tập test chính.

| Horizon | Cửa sổ còn | RF không sáng | RF có sáng | Persistence |
|---|---:|---:|---:|---:|
| 30 | 394 | 6.7260 | 6.7242 | 0.6468 |
| 60 | 383 | 6.7661 | 6.7519 | 0.9901 |

## Quan hệ ánh sáng–soil

Pearson trên các phút soil hợp lệ đã đối soát và trên sai phân một phút liền kề (không nối qua gap):

| Phiên | Mức ADC–soil | Sai phân ADC–soil |
|---|---:|---:|
| W01 | 0.0560 | 0.0926 |
| W02 | -0.0517 | 0.0418 |
| W03 | -0.0110 | 0.0160 |
| W04 | 0.2443 | -0.0713 |

Các hệ số chỉ mô tả dữ liệu, không chứng minh ánh sáng gây khô đất. Giờ trong ngày, nhiệt độ/độ ẩm không khí, phân bố nước, tự tương quan và bão hòa có thể gây nhiễu. Chưa dùng kiểm định p-value từ các mẫu thời gian phụ thuộc.

## Tái lập

```bash
PYTHONPATH=ai .venv-ai/bin/python -m smart_green_ai.light_experiment --output artifacts/light-experiment-new-run
PYTHONPATH=ai .venv-ai/bin/python -m pytest ai/tests/test_light_features.py -q
node backend/tests/dashboard_controls.test.cjs
```

Output phải là thư mục mới; script từ chối ghi đè. Chạy từ gốc repository có W01–W04. Bundle `.joblib` chỉ nạp từ nguồn tin cậy. `summary.json` lưu versions, input SHA-256, chất lượng và MAE; mỗi horizon có 4 bundle, CSV dự đoán chung và report.json. Không cấu hình các bundle này vào backend production.

Mã mới: `ai/smart_green_ai/light_features.py`, `light_experiment.py`. AI v2 và mô hình cũ không sửa. Dashboard thêm đồ thị ADC riêng và xu hướng theo kiểm tra thực nghiệm garden-01, chặn suy diễn khi cũ/thiếu/reset/bão hòa; chưa gán thiếu/thừa sáng. Nhật ký thêm các mốc quan sát có timestamp và xuất trong ZIP.

Hướng dẫn W05: [W05_LIGHT_COLLECTION_GUIDE.md](W05_LIGHT_COLLECTION_GUIDE.md).

## Kiểm thử và trạng thái bàn giao

- AI và bộ dựng dataset: 42 test đạt.
- Backend (gồm PostgreSQL kiểm thử riêng): 102 test đạt.
- Dashboard Node: 22 test đạt.
- Đã nạp lại bundle và đối chiếu dự đoán/MAE; kiểm tra hash bằng chứng W01–W04 không đổi.
- Chưa kiểm tra giao diện bằng trình duyệt thật; chưa restart hoặc triển khai backend đang chạy. Không gửi lệnh thiết bị; không xác nhận trạng thái AUTO trực tiếp từ phần cứng. Khi thu W05 cần kiểm tra OFF theo hướng dẫn.
- Trạng thái triển khai ở trên ghi nhận tại lúc kiểm thử; việc commit/push mã nguồn không tự triển khai backend.
