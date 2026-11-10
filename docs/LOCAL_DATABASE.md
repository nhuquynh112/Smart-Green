# PostgreSQL và pgAdmin trên máy

Database đang chạy bằng Docker Compose. Backend FastAPI chạy trên máy và tiếp tục nhận dữ liệu ESP32 qua URL LAN hiện tại.

## Máy mới / TV2 kéo code về

Từ thư mục gốc repo, dùng Python 3.11+ và Docker Desktop đang chạy:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,report]" -r backend/requirements.txt
python tools/setup_local_database.py
docker compose up -d
python -m backend.run_local --host 127.0.0.1
```

Windows: thay lệnh activate bằng `.venv\Scripts\Activate.ps1` trong PowerShell.

Script setup tạo `.env`, `pgpass` và `runtime-env.json` với mật khẩu ngẫu nhiên; nếu có cấu hình cũ sẽ dừng, không ghi đè. Lần đầu backend khởi động sẽ tạo schema 5 bảng. Không chạy seeder vào database thu thật. Database mới không có dữ liệu và không có model AI thật; trạng thái AI unavailable là bình thường.

Khi nối ESP32, thay `127.0.0.1` ở lệnh backend bằng IP LAN của **máy đang chạy backend**. Điền URL, device ID và API key tương ứng vào `firmware/include/site_config.h` local; giữ telemetry-only và AI disabled. Không dùng IP/mật khẩu của máy khác. Model demo là tùy chọn, không phải điều kiện nhận telemetry.

## Xem dữ liệu

Mở http://127.0.0.1:5050, chọn:

**Servers → Smart Green → Databases → smart_green_local → Schemas → public → Tables → telemetry**.

Bấm phải `telemetry` → **View/Edit Data → Last 100 Rows** (hoặc All Rows). Trong Query Tool có thể chạy:

```sql
SELECT device_id, boot_id, sample_seq, measured_at, received_at,
       soil_pct, temperature_c, humidity_pct, pump_running
FROM telemetry
ORDER BY received_at DESC
LIMIT 100;
```

pgAdmin dùng chế độ desktop trên localhost nên không cần đăng nhập riêng. Kết nối Smart Green đã được cấu hình sẵn; mật khẩu PostgreSQL lấy từ file local, không đưa vào Git.

## Bật/tắt

Mở Docker Desktop, sau đó chạy từ thư mục gốc dự án:

```bash
docker compose up -d
```

Mở pgAdmin bằng đường dẫn phía trên. Nếu backend chưa chạy:

```bash
.venv-ai/bin/python -m backend.run_local --host "<BACKEND_LAN_IP>"
```

Xem trạng thái: `docker compose ps`. Dừng database và pgAdmin: `docker compose stop`.

Dữ liệu nằm trong volume `smart-green_postgres_data`; thiết lập giao diện nằm trong `smart-green_pgadmin_data`. Dừng container không xóa dữ liệu. Không dùng `docker compose down -v` nếu còn cần dữ liệu.

## Kết nối

- Từ máy: host `127.0.0.1`, port `55432`, database `smart_green_local`, user `ad`.
- Từ pgAdmin container: host `postgres`, port `5432`.
- `.env` chứa mật khẩu Docker; `artifacts/backend-local/runtime-env.json` chứa cấu hình backend; đều được Git bỏ qua.
- `artifacts/backend-local/pgpass` cấp mật khẩu cho kết nối pgAdmin. File được container sao chép vào `.pgpass` khi khởi động.
- Chỉ mở PostgreSQL/pgAdmin trên localhost. Đây là cấu hình phát triển cá nhân.

## Chuyển dữ liệu ngày 09/11/2026

Đã chuyển 44 mẫu telemetry và 1 thiết bị từ cluster local sang Docker. Nội dung cả 5 bảng được so sánh bằng SHA256 sau chuẩn hóa JSON, khớp hoàn toàn. Database nguồn đã dừng và được giữ ở `artifacts/backend-local/pgdata`; bản dump ở `artifacts/backend-local/before-docker.dump`. Báo cáo đối chiếu ở `artifacts/backend-local/docker-migration.json`.

Cấu hình PostgreSQL qua Unix socket trong báo cáo phiên trước là cấu hình lịch sử. Backend hiện dùng PostgreSQL Docker qua TCP.

Tham khảo cấu hình container chính thức: https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html

## Quy trình tải và cài đã thực hiện

1. Máy đã có Docker Desktop và Docker Compose, nên không cần cài lại Docker.
2. Tạo `compose.yaml` để mô tả hai dịch vụ: `postgres:16` và `dpage/pgadmin4:9.19`. Đây là các image chứa phần mềm cùng môi trường chạy.
3. Tạo mật khẩu trong `.env`, cấu hình kết nối Smart Green ở `docker/pgadmin/servers.json` và file mật khẩu local cho pgAdmin.
4. Chạy `docker compose up -d`. Docker tự tải image còn thiếu, tạo container, mạng nội bộ và volume lưu dữ liệu. Không phải tải riêng bộ cài PostgreSQL hoặc pgAdmin lên máy.
5. Sao lưu database cũ, phục hồi vào PostgreSQL Docker, so sánh dữ liệu cả 5 bảng rồi đổi cấu hình backend sang database mới.
6. Mở http://127.0.0.1:5050 để xem dữ liệu bằng pgAdmin. ESP32 vẫn gửi tới FastAPI; FastAPI mới là thành phần ghi PostgreSQL.

Lần sau trên máy này chỉ cần mở Docker Desktop rồi chạy `docker compose up -d` nếu container chưa chạy; Docker dùng lại image và dữ liệu đã có. File `.env` và cấu hình private đã tạo trên máy này không nằm trong Git; nếu clone sang máy khác cần tạo chúng trước.
