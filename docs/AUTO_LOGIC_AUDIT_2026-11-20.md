# Kiểm tra logic AUTO bằng mô phỏng ngày 20/11/2026

**32 ca AUTO trên lõi C++ đều PASS; bộ Python đạt 185 tests và 8 subtests, 8 biến thể PostgreSQL SKIP. Không có FAIL trong các test đã chạy. Có một rủi ro đọc mã ở luồng ACK/STOP cần xử lý hoặc xác nhận thêm; chưa thể phê duyệt toàn bộ AUTO trên phần cứng.**

Không sửa Dashboard, không xây lại AUTO, không sửa logic production, không nạp firmware, không mở Serial, không gọi IP thiết bị hoặc database thu dữ liệu. Toàn bộ output trong bài kiểm tra mới là biến bool của fake PumpOutput; C++ chạy trên máy tính. Các test HTTP hiện hữu chỉ bind loopback với server mô phỏng.

## Cơ sở kiểm tra

- Commit mã production: `da88dd9` trên `tv1/firmware-ai-foundation`.
- Lõi thật dùng trong mô phỏng: `firmware/include/controller.h`, `pump_guard.h`, `protocol.h`; bridge hiện hữu `firmware/test/native/runtime_bridge.cpp`.
- Backend thực `create_app` với SQLite `:memory:`; test xuyên lớp mới gọi handler, không giả lập kiểm tra auth. Auth/HTTP có các test riêng trong suite hiện hữu.
- Cấu hình an toàn đọc được từ file local (chỉ danh sách trường cho phép; không xuất Wi-Fi/key): low=30, high=45, pulse=maxPulse=1000 ms, cooldown AUTO=600000 ms, manualCooldown=0, quota=20 lần/20000 ms, AI commands=false. Đây là cấu hình source local, không xác nhận bản đang nạp trên ESP32 hay trạng thái mode hiện tại.
- Native audit dùng ngưỡng/pulse/quota như trên, rút cooldown xuống 1000 ms ở phần lớn ca để dễ kiểm tra mốc; A14 kiểm tra đúng 600000 ms. Mọi thời gian là thời gian ảo, không chờ bơm.
- Freshness trong core: mẫu soil hợp lệ đến 4000 ms (bao gồm biên); 4001 ms bị loại. AUTO chỉ dựa soil/phao/đồng hồ và guard, không dùng AI hay ADC ánh sáng. DHT lỗi không tự động đồng nghĩa soil lỗi.

## Ma trận AUTO trên lõi C++

| Mã | Tình huống và tiêu chí | Kết quả |
|---|---|---|
| A01 | Soil đúng 30: cần 3 mẫu khô khác nhau mới bắt đầu | PASS |
| A02 | Gọi tick nhiều lần với cùng sampledMs không đủ 3 mẫu | PASS |
| A03 | Soil 30,01 giữa chuỗi khô đặt lại bộ đếm | PASS |
| A04 | Đang chạy ở 44,99; dừng tại 45; vùng 30–45 không tự khởi động lại | PASS |
| A05 | Phao thiếu nước trước khi bắt đầu: không chạy, không sinh event | PASS |
| A06 | Mất nước khi đang chạy: OFF, event Tank | PASS |
| A07 | soil_valid=false chặn chạy, phá chuỗi 3 mẫu và dừng xung đang chạy | PASS |
| A08 | NaN/Inf/soil âm/>100 trước khi chạy đều bị chặn | PASS |
| A09 | Soil cũ chặn bắt đầu và dừng xung; reason Sensor | PASS |
| A10 | Biên freshness 4000/4001 ms đúng | PASS |
| A11 | Tự dừng đúng 1000 ms; event RULE, command_seq=0, giữ reservation | PASS |
| A12 | STOP và SET_MODE OFF trùng/hết hạn, kể cả clock chưa có, vẫn OFF và không tự chạy lại | PASS |
| A13 | OFF/MANUAL không tự chạy luật AUTO dù soil khô | PASS |
| A14 | AUTO chờ đủ 10 phút sau boot/dừng; manualCooldown=0 không bỏ qua | PASS |
| A15 | Đủ 20 lần AUTO bị chặn dù MANUAL được bỏ giới hạn số lần | PASS |
| A16 | Còn 500 ms ngân sách không đủ xung AUTO 1000 ms: từ chối | PASS |
| A17 | Còn đúng 1000 ms: được chạy; dừng sớm không hoàn ngân sách | PASS |
| A18 | Ngân sách MANUAL hết không tiêu hao/thay thế ngân sách AUTO | PASS |
| A19 | Cửa sổ quota 24 giờ chưa hết bị chặn; đúng 86400 giây reset ngân sách | PASS |
| A20 | Chưa có UTC hoặc UTC lùi trước lần tưới cuối: không bắt đầu | PASS |
| A21 | Chưa commissioning, config sai hoặc lưu trữ lỗi: không bắt đầu | PASS |
| A22 | Output start thất bại/heartbeat guard: latch fault, không chạy lại | PASS |
| A23 | Log đủ 32 event chặn tưới; chỉ ACK event đầu mới giải phóng chỗ | PASS |
| A24 | Không ACK event Running; event đã dừng ACK một lần; quota không được hoàn | PASS |
| A25 | Reset giữa xung: output mô phỏng OFF, event Reboot, quota còn nguyên | PASS |
| A26 | Không gọi server: AUTO vẫn chạy cục bộ và dừng theo thời lượng/phao | PASS |
| A27 | Guard heartbeat 500/501 ms, phao và thời lượng đúng biên | PASS |
| A28 | Lưu trữ lỗi lúc dừng: output OFF trước, không chạy lại | PASS |
| A29 | State mới chưa có chế độ lưu: boot OFF | PASS |
| A30 | State đã lưu AUTO: reset giữ AUTO; sau cooldown + mẫu khô có thể chạy lại | PASS theo hành vi hiện tại; xem lưu ý dưới |
| A31 | NaN/Inf/soil âm/>100 trong xung AUTO: dừng với reason Sensor | PASS |
| A32 | millis tràn uint32 vẫn dừng đúng hạn xung AUTO | PASS |

A30 không phải chứng minh chính sách “mọi reset đều chuyển chế độ OFF”. Mã hiện tại chỉ tắt output lúc boot, vẫn khôi phục chế độ AUTO đã lưu. Nếu yêu cầu vận hành là phải có thao tác xác nhận lại sau reset thì **yêu cầu đó hiện chưa đạt**; không tự thay chính sách trong đợt kiểm tra này.

Bộ đếm ba mẫu khô là bộ đếm độ ẩm, không yêu cầu ba mẫu liên tiếp đều có tankOK. Khi đã đủ mẫu khô lúc bình thiếu nước, phao trở lại đủ nước có thể cho phép bắt đầu ngay nếu các guard/cooldown khác đạt. Đây là hành vi được test, không phải vô tình bỏ qua phao.

## Backend, mạng và nhật ký

| Ca | Bằng chứng | Kết quả |
|---|---|---|
| AUTO được ACK chỉ đổi mode, chưa tự coi bơm đã chạy | `test_auto_rule_event_backend_retry_conflict_and_fifo_ack` / enable_auto | PASS |
| Event AUTO RULE command_seq=0 được backend lưu, gửi lại không nhân đôi | Test trên, SQLite thật trong bộ nhớ | PASS |
| Cùng event_id nhưng actual_ms khác bị 409; đúng ACK mới bỏ event ở core | Test trên | PASS |
| STOP và SET_MODE OFF dừng AUTO đang chạy, hủy AUTO pending trước đó | `test_backend_stop_or_off_ends_running_auto_and_supersedes_pending`, 2 biến thể | PASS |
| ACK chế độ AUTO không vượt kiểm tra mẫu cũ/phao/cảm biến tại core | `test_auto_mode_ack_does_not_override_stale_or_empty_sensor` | PASS |
| Mất ACK, reboot, phát lại lệnh không tưới hai lần; khôi phục event | `integration/test_http_runtime.py::test_lost_command_ack_reboot_and_event_recovery` | PASS |
| Server chậm/time-out không chặn core tự dừng; telemetry retry không nhân đôi | `test_server_slow_core_still_can_stop_and_telemetry_retries` | PASS trong loopback/giờ ảo |
| Backend lưu event nhưng response mất: retry idempotent | `test_event_saved_but_response_lost_is_idempotent` | PASS |
| Lệnh hết hạn/sai thiết bị/auth sai không bật output | `test_expired_wrong_device_and_auth_never_start` | PASS |
| AUTO không có server vẫn bị phao khóa/dừng | `test_auto_without_server_respects_empty_tank` | PASS |
| UI kiểm tra polling/ACK/expiry/quota, không thêm UI | Suite `backend/tests/dashboard_controls.test.cjs` | PASS; DOM mô phỏng |
| PostgreSQL concurrency và session variants | Chưa có SG_TEST_POSTGRES_ADMIN_URL cho database test riêng | SKIP 8, không tính PASS |

Bộ Python toàn dự án: **185 passed, 8 skipped, 8 subtests passed**. Tệp JUnit ghi kết quả từng test. Bộ firmware hiện hữu (controller, safety, runtime, profile, telemetry time) đều đạt. Đếm test toàn dự án không đồng nghĩa tất cả 185 test chỉ kiểm tra AUTO.

## Điểm phát hiện cần theo dõi

### R01 ACK lỗi kéo dài có thể chặn nhận STOP

Trong `firmware/include/network_worker.h`, worker chỉ GET lệnh mới khi `!pendingAck && !waitingCore`. `pendingAck` chỉ được xóa khi POST ACK trả 2xx. Nếu ACK lệnh trước liên tục bị 404/500 hoặc lỗi đường truyền, GET lệnh STOP tiếp theo không được thực hiện dù endpoint GET có thể vẫn truy cập được. Backend có thể đã xếp STOP nhưng thiết bị chưa nhận; AUTO cục bộ vẫn có thể chạy theo quota/cooldown.

**Trạng thái: phát hiện qua đọc mã, chưa fault-injection trực tiếp task mạng ESP32.** Test loopback hiện tại không thực thi FreeRTOS worker; không đánh dấu đường này PASS. Đề xuất tách xử lý STOP ưu tiên khỏi hàng ACK đang retry và giữ nguyên chống lặp trước khi triển khai. Chưa sửa firmware trong phạm vi audit.

### R02 Reset giữ chế độ AUTO

A25/A30 xác nhận output lúc tạo lại controller là OFF nhưng mode AUTO lưu vẫn còn. Sau đủ cooldown, giờ hợp lệ và mẫu khô, AUTO có thể khởi động lại. Không mô tả reset như một cách tắt AUTO lâu dài. Muốn tắt chế độ phải có STOP/OFF được thiết bị nhận/xác nhận; khi mất mạng không thể bảo đảm lệnh web tới ngay.

### R03 AUTO cục bộ dùng mẫu mới tại ESP32, không dùng tuổi dữ liệu Dashboard

Telemetry trên Dashboard có thể cũ khi mất mạng trong khi cảm biến cục bộ vẫn mới. Theo thiết kế hiện tại, AUTO vẫn được phép chạy nếu clock/sensor/phao/guard/quota hợp lệ. Test backend chặn WATER với telemetry cũ không có nghĩa AUTO cục bộ bị tắt. SET_MODE AUTO được backend xếp là yêu cầu đổi mode; firmware quyết định có được tưới hay không.

### R04 Ngưỡng và hiệu chuẩn chưa phải bằng chứng nhu cầu nước của cây

30/45 là ngưỡng chỉ số soil tương đối hiện tại. Mẫu điện hợp lệ và test PASS không chứng minh chỉ số này phản ánh đủ ẩm/khô cho cây thực. Cảm biến lệch nhưng vẫn báo valid có thể làm AUTO tưới nhiều lần đến quota. Cần nghiệm thu hiệu chuẩn, vị trí cảm biến và lưu lượng; không tăng quota dựa trên các test này.

## Những phần không thể xác nhận chỉ bằng mô phỏng

| Hạng mục | Trạng thái |
|---|---|
| GPIO/relay thực sự OFF khi boot/reset, mức active-low, relay kẹt | CHƯA XÁC NHẬN |
| Motor dừng, nước còn chảy do siphon, thể tích mỗi xung | CHƯA XÁC NHẬN |
| Phao đấu đúng, nhiễu/dội, độ trễ ngắt thực | CHƯA XÁC NHẬN |
| Độ trễ esp_timer/FreeRTOS/flash write khi tải cao | CHƯA XÁC NHẬN; guardReason chỉ được test như hàm thuần |
| NVS thật khi mất điện giữa ghi, hỏng flash/nguồn sụt áp | CHƯA XÁC NHẬN; Store giả chỉ mô phỏng save thành công/thất bại |
| Wi-Fi reconnect, NTP drift, task ACK bị lỗi kéo dài trên ESP32 | CHƯA XÁC NHẬN trực tiếp |
| Firmware/config đang nạp và AUTO hiện có bật hay không | KHÔNG TRUY VẤN THIẾT BỊ trong audit |
| PostgreSQL thật và tải đồng thời ngoài môi trường test | CHƯA XÁC NHẬN trong lượt này |

## Chạy lại an toàn trên máy tính

```bash
bash tools/test_auto_audit.sh
bash tools/test_firmware.sh
PYTHONPATH=ai OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv-ai/bin/python -m pytest -q ai/tests backend/tests tools/tests integration
node --test backend/tests/dashboard_controls.test.cjs
```

Cần g++, môi trường Python và ArduinoJson đã có tại thư mục libdeps để build bridge/test runtime. Không chạy `pio upload`, không cần cắm USB. Các suite HTTP có thể cần quyền bind localhost trong môi trường sandbox. Không trỏ biến test PostgreSQL vào database thu dữ liệu.

Chi tiết: [kết quả 32 ca native](auto-audit-20261120/native-results.txt), [Python](auto-audit-20261120/pytest-results.txt), [JUnit](auto-audit-20261120/pytest-results.xml), [firmware](auto-audit-20261120/firmware-results.txt), [Dashboard](auto-audit-20261120/dashboard-results.txt). Checksum mã đã kiểm tra và bằng chứng: `auto-audit-20261120/manifest.json`.
