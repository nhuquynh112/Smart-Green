# GitHub tham khảo — kiểm tra ngày 29/10/2026

Đã kiểm tra README/cây thư mục và một số file nguồn, chưa build hay kiểm thử phần cứng của các repo này. Không repo nào dưới đây đã được xác nhận đáp ứng toàn bộ đặc tả Smart-Green.

| Repository | Nên học | Khác biệt/giới hạn |
|---|---|---|
| [Opeyemi-Builds/AgroSense-IoT-Smart-Irrigation-System](https://github.com/Opeyemi-Builds/AgroSense-IoT-Smart-Irrigation-System) | Tách firmware/backend/frontend, ESP32 tưới cục bộ, FastAPI nhận telemetry | README mô tả dashboard chỉ đọc; advisor dùng rule/LLM, không phải mô hình hồi quy độ ẩm 30 phút |
| [aqib-ai-ml/soil-irrigation-system](https://github.com/aqib-ai-ml/soil-irrigation-system) | Sketch ESP32, DHT11, ADC độ ẩm, web đơn giản | Code map ADC bằng số cố định; lỗi DHT trả 0. Với đồ án phải hiệu chuẩn lại và biểu diễn lỗi bằng null/cờ |
| [vinayakjoshi04/Smart-Irrigation-System](https://github.com/vinayakjoshi04/Smart-Irrigation-System) | Cấu trúc ESP32 + Python + notebook, command_id, quản lý phiên | Dùng Flask và dự đoán lượng nước theo thông tin nông nghiệp; không dự đoán độ ẩm tương lai của một chậu |
| [itsmanask/AgroSmart](https://github.com/itsmanask/AgroSmart) | Pipeline Random Forest và xuất mô hình cho ESP32 | Có dataset_generator.py sinh nhãn từ quy tắc và số ngẫu nhiên; là phân loại tưới/không tưới, không dùng accuracy đó làm bằng chứng trên đất thật |
| [aqib-ai-ml/ai-powered-smart-irrigation](https://github.com/aqib-ai-ml/ai-powered-smart-irrigation) | Ý tưởng ghép ESP32 và Python prediction API | Cây root lúc kiểm tra chỉ có README, video, CSV, predict_server.py, requirements; chưa thấy nhiều file/thư mục huấn luyện/firmware mà README nêu. Không chọn làm nền đầy đủ |

Ưu tiên đọc AgroSense để hiểu kiến trúc; sketch soil-irrigation-system để học đọc cảm biến; Smart-Irrigation-System để xem đường dự đoán/lệnh. Giữ bài toán hồi quy 30/60 phút của nhóm. Nếu tái sử dụng mã phải kiểm tra LICENSE cụ thể và ghi nguồn; repo public không tự đồng nghĩa được phép sao chép mọi cách.
