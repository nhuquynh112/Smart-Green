import csv
import json
from pathlib import Path

# Tìm file log mới nhất
files = list(Path("logs").glob("device-monitor-*.log"))

if not files:
    raise SystemExit("Không tìm thấy file log!")

latest = max(files, key=lambda p: p.stat().st_mtime)

records = []
invalid = 0

# Đọc từng dòng JSON
for line in latest.read_text(
    encoding="utf-8", errors="replace"
).splitlines():
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        invalid += 1
        continue

    if isinstance(data, dict) and "soil_raw" in data:
        records.append(data)

if not records:
    raise SystemExit("Không có dữ liệu JSON hợp lệ!")

# Tạo thư mục lưu dữ liệu
Path("data").mkdir(exist_ok=True)

output = Path("data/bench_clean.csv")

# Ghi dữ liệu thành CSV
columns = list(dict.fromkeys(
    key for record in records for key in record
))

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)

print(f"File nguồn: {latest}")
print(f"Số bản ghi hợp lệ: {len(records)}")
print(f"Số dòng lỗi: {invalid}")
print(f"Đã lưu: {output}")