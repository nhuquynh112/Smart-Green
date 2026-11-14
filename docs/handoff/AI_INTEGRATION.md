# TV1 → TV2: tích hợp AI v2 và dữ liệu

Cập nhật 08/11/2026. Backend/Web/PostgreSQL do TV2 triển khai. TV1 cung cấp mã Python, schema dữ liệu, mock và kiểm thử offline. Tài liệu này không tự tạo hoặc gửi lệnh WATER.

## Những file cần đọc

| File | Dùng để làm gì |
| --- | --- |
| `docs/TV2_CONTRACT.md` | Telemetry, command, ACK, event và mã phản hồi |
| `docs/WATERING_AND_AI_DATASET.md` | Nhật ký tưới tay/bơm và tổng hợp CSV phút |
| `ai/smart_green_ai/features.py` | Schema/đặc trưng v2 và lọc cửa sổ |
| `ai/smart_green_ai/inference.py` | Hàm dự đoán chỉ trả đề xuất |
| `tools/mock_tv2.py` | Mock RAM để thử logic, không thay database |
| `integration/test_http_runtime.py` | Các ca tích hợp core/protocol với HTTP localhost |

## Hợp đồng CSV AI v2

Một dataset chỉ có một device, calibration, nguồn real/synthetic và time_basis.

Các cột bắt buộc: `timestamp`, `device_id`, `calibration_id`, `data_origin`, `soil_pct`, `temperature_c`, `humidity_pct`, `minutes_since_water`, `water_event_count`.

`time_basis` phải được cung cấp trong luồng mới: `device_timestamp`, `received_at_proxy` hoặc `synthetic` (chỉ dữ liệu mô phỏng). Code hỗ trợ CSV không có cột này theo quy ước giờ đo; không được bỏ cột để che nguồn proxy.

- Timestamp là đầu phút UTC, chỉ dùng sau khi phút hoàn tất. Tính median từ mẫu trong phút, không lấy mẫu tương lai.
- Đếm tưới tay/bơm bằng `water_event_count`; không giả ms cho tưới tay. Thể tích ml và actual_ms là metadata riêng.
- Sự kiện không rõ thời điểm, reboot giữa bơm hoặc mất nhật ký: đánh dấu không đủ thông tin; không tự điền 0.
- Bộ đếm là theo phiên, không giảm hoặc reset trong cùng dataset. Khi bắt đầu phiên mới, tạo dataset riêng.
- Muốn dùng giờ nhận làm trục thay thế phải ghi `received_at_proxy`, lưu nguyên raw và đánh giá độ trễ. Không tự chuyển toàn bộ dữ liệu cũ sang giờ đo.

Model v1 phải huấn luyện lại, không chỉ sửa chuỗi version trong metadata.

## Gọi dự đoán trong backend

Chỉ nạp model do nhóm tạo và tin cậy. Nạp một lần lúc khởi động worker; không nhận đường dẫn joblib/pickle tùy ý từ request. Dùng phiên bản thư viện trong report của model.

```python
import joblib
import pandas as pd
from smart_green_ai.inference import predict

bundle = joblib.load('artifacts/candidate-v2/candidate.joblib')

# recent là DataFrame chứa ít nhất 16 phút liên tiếp đã hoàn tất,
# cùng thiết bị/calibration/origin/time_basis và không tưới trong 15 phút gần nhất.
try:
    advice = predict(bundle, recent, now=pd.Timestamp.now(tz='UTC').isoformat())
except ValueError as exc:
    result = {'status': 'unavailable', 'reason': str(exc), 'can_trigger_pump': False}
else:
    result = {'status': 'available', **advice}
```

`recent` do backend tạo theo schema trên, không lấy CSV synthetic làm dữ liệu cây thật. Hàm kiểm tra feature_version, tuổi dữ liệu, calibration/origin/time_basis; phút chưa hoàn tất hoặc quá 120 giây kể từ cuối phút bị từ chối. Backend phải log các lỗi vận hành khác và trả trạng thái unavailable, không suy ra lệnh tưới từ lỗi.

Đầu ra có `predicted_soil_pct`, `horizon_minutes`, `as_of` (đầu phút), `available_at` (cuối phút), `time_basis`, `model`, `conditional_on=no_additional_irrigation`, `can_trigger_pump=false`. Dashboard nên ghi rõ đây là dự đoán có điều kiện và hiển thị lúc dữ liệu được cập nhật.

Việc ánh xạ đề xuất thành command AI chưa được phê duyệt bằng dữ liệu thực nghiệm. Giữ `SG_AI_COMMANDS_ENABLED=false`; Auto-Rule trên ESP32 vẫn là lớp kiểm tra an toàn khi được nghiệm thu.

## Kiểm thử backend thật khi TV2 sẵn sàng

| Ca | Kết quả yêu cầu |
| --- | --- |
| Telemetry gửi lại cùng identity | Một bản lưu, ACK thành công |
| Cùng identity nhưng payload khác | 409 hoặc lỗi tương đương đã thống nhất; không ghi đè |
| Sai key hoặc sai device | Không đọc/ghi dữ liệu thiết bị khác |
| Mất phản hồi sau khi lưu event | Gửi lại trả đúng event_id, không nhân bản |
| Lệnh đã thực thi nhưng mất ACK | Gửi lại cùng sequence, không tạo lệnh mới để retry |
| Lệnh hết hạn/sai kiểu | Từ chối, không đổi trạng thái bơm |
| ACK started | Chỉ biểu thị đã bắt đầu; chờ event để kết luận kết thúc |
| AI thiếu dữ liệu/sai version/calibration/clock | unavailable, không gửi WATER |
| Sự kiện Reboot | actual_ms=null, không suy thành 0 hoặc ml |

Mock và kiểm thử hiện không chứng minh giao dịch/constraint PostgreSQL hoặc cơ chế phân quyền backend thật đã đúng. TV2 phải chạy lại các ca trên hệ thống của mình.

## Thông tin TV2 cần trả lại

URL backend phát triển truy cập được từ LAN; device ID; cách cấp key riêng ngoài Git; CA nếu HTTPS; xác nhận response schema và timestamp; bằng chứng lưu DB, ACK và xử lý lệnh trùng. Chưa cần gửi mật khẩu hay API key vào tài liệu bàn giao.
