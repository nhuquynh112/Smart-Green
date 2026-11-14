# Sao lưu W04

Gói `artifacts/w04-20261114-reviewed.zip` chứa dữ liệu gốc W04, nhật ký, dữ liệu phút, dự đoán, mã đánh giá, báo cáo và manifest SHA-256. File `.zip.sha256` đi kèm dùng kiểm tra gói.

Đây là bản sao lưu phiên W04, không phải backup toàn bộ PostgreSQL. Không chứa cấu hình runtime hoặc mật khẩu kết nối. Mô hình W01 được tham chiếu bằng đường dẫn và checksum trong báo cáo; không nhân bản mô hình vào ZIP W04.

Kiểm tra tại gốc repository:

```bash
(cd artifacts && sha256sum -c w04-20261114-reviewed.zip.sha256)
.venv-ai/bin/python artifacts/session-w04-2026-11-14/verify_evidence.py
```

Giải nén vào thư mục riêng để xem dữ liệu, không import vào DB đang thu. Script verify cần đầy đủ bằng chứng W01–W03 trong repository. Không chạy script export khi chỉ muốn đọc gói offline.
