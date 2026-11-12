# Bằng chứng AWS medium — 09/11/2026

Các file này được xuất từ kết quả chạy thật, chỉ chọn metadata và kết quả đã lọc mật khẩu/cookie/token. Không gồm state, saved plan, secret JSON hoặc payload backup. Account/resource IDs dùng để đối chiếu môi trường lab.

| File | Nội dung |
|---|---|
| [http-source.json](http-source.json), [http-restored.json](http-restored.json) | 47 kiểm tra HTTPS đạt trên mỗi site |
| [fixture.json](fixture.json), [fixture-audit.json](fixture-audit.json) | Course/user/assignment/submission IDs, điểm/hash; enrolment/role và chính sách assignment đọc từ Moodle thật; không chứa password |
| [inventory.json](inventory.json) | Compute/private IP, RDS/EFS/Redis, route/SG, ALB/CloudFront, health, logs/alarms tại lúc kiểm kê nguồn |
| [asg-replacement.json](asg-replacement.json) | Instance trước/sau và kiểm tra cookie/hash trong lúc thay app; không lưu cookie |
| [nodes.json](nodes.json) | Cùng artifact, EFS và log file riêng trên cả hai app của nguồn/đích |
| [cluster-probes.json](cluster-probes.json) | Moodle lock giữa hai node và cache MUC A→B |
| [purge-session.json](purge-session.json) | 20 request dùng cùng cookie sau purge cache |
| [operations.json](operations.json) | Command ID và bước release, backup, restore, maintenance gate, TLS proof |
| [backup.json](backup.json) | Backup prefix, timestamp, hash payload và reference artifact |
| [state-lock.json](state-lock.json) | Plan thứ hai bị S3 lock thật từ chối trong lúc apply |
| [cleanup.json](cleanup.json) | Kiểm kê sau khi dọn 71 tài nguyên restore, snapshot cuối và lịch xóa secret tạm; lab chính được giữ chạy |

Các ca còn chờ và giới hạn kết quả xem [nhật ký AWS](../../12-medium-live-lab.md). URL restore chỉ phục vụ drill; lab nguồn được giữ chạy theo yêu cầu người dùng.
